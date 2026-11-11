#!/usr/bin/env python3
"""Which shipped versions were actually LOOKED AT by a different model family, and which were not.

WHY THIS EXISTS, and it is not a nice-to-have. Konyo's standing order since 2026-07-15 is one
Grok pass after every ship — "its like ping pong. you fix and ship and then ask it what can be
perfected". On 2026-08-26 I shipped v2137, v2138, v2139, v2140, v2141 and v2142 and ran ZERO. He
asked whether the second eye was running; the honest answer was no, and nothing anywhere had
noticed, because nothing anywhere was keeping score. A standing order that lives only in memory is
a standing order that lapses silently.

So it is written down. This module is the score, and hooks/pre-push reads it.

WHAT MAKES THIS DIFFERENT FROM A CHECKBOX — every one of these is a scar this repo already paid for:

  · AN UNREACHABLE EYE IS AN EMPTY SEAT, NEVER AGREEMENT. `reached=False` is recorded, kept, and
    does NOT satisfy the gate. A dead CLI must never read as "it looked and was happy" — that is
    the exact defect that let a Grok-hardwired third eye sit permanently empty on every machine but
    his while every lamp stayed green.
  · A SKIP IS NOT A PASS. No entry at all for a version is a REFUSAL, not a shrug.
  · A COURIER IS NOT A REVIEW. The entry carries the model id, the images actually handed over, and
    the head of the raw answer. A same-family agent writing plausible strings must never be
    mistakable for a cross-family look, so `family` is derived from the model id, not asserted.
  · IT MUST BE ABLE TO GO RED. tests/../test_control.py drives both directions; a gate never seen
    red is measuring nothing.

The record itself is a runtime record of DECISIONS, like .console_scars.json and
reel_tombstones.json, so it lives untracked beside them rather than in git.

=== HOW TO ASK, AND IT COST ME THREE LOOKS TO LEARN — 2026-09-06 ===
⚠⚠ A PRECISE QUESTION ABOUT THE WRONG PROPERTY IS STILL THE WRONG MEASUREMENT.
[[heartov2]] is two text overlaps on the heart's lock fan, 62x5 and 25x10 px, measured by
overlap_ratchet and confirmed present at that width. I asked the second eye, three separate times,
the direct question: "is any label drawn ON TOP OF another label or number?" — once even naming
the radial diagram and once on a 3x magnified crop. Three times it answered "cleanly separated",
and three times that was an HONEST answer: it cannot adjudicate whether two named glyphs intersect
at five pixels. I read that as "nothing is wrong there" and recorded, twice, that the second eye
was simply the wrong instrument for this defect.

Then I asked an OPEN question — "one thing a careful owner would fix before showing this to
someone else" — and it named the fan unprompted:
    "dense overlapping lines + labels around the heart (esp. lower-right cluster near
     'vault.target', 'prune.arm', 'mini auto.run') make the diagram unreadable"
It also named `mini auto.run` independently, which is the exact label render_check reports CLIPPED
at 375. Two instruments, different mechanisms, same label.

SO EVERY LOOK SHOULD CARRY BOTH SHAPES:
  · CLOSED questions ("is X truncated", "do these two numbers contradict") — they pin specific
    regressions and their answers are checkable.
  · AT LEAST ONE OPEN question ("what would an owner fix first", "what is hard to read here") —
    this is where a defect nobody thought to ask about arrives.
A look made only of closed questions can only confirm or deny what the asker already suspected,
which is the smaller half of what a different family of eyes is for.
⚠ AND "UNKNOWN is preferred over a guess" belongs in the ask, every time. It is what makes
"no numeric pairs to compare at all" available as an answer instead of a false "they agree".
"""

import collections
import copy
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)

# ══ #178 (REG-2450) — ONE SECOND-EYE LEDGER PER MACHINE, NOT ONE PER CHECKOUT ═══════════════════════════════════════
# MEASURED 2026-10-22 (Push A1): the ship gate (`--check <prev> --gate`) read the PUSHING tree's tv/.second_eye.jsonl. A
# fresh push worktree has none, so v3784 was refused ("v3783 OWES A LOOK - nothing was ever recorded"); and push #13's
# worktree held the v3778 look, which died with that worktree (main's ledger then ended at v3760). A look that happened
# was LOST - the defect class of the red memory (REG-2342) and the verdict cache (REG-2340). So:
#   · THE LEDGER LIVES IN GIT'S COMMON DIR (<common>/second_eye.jsonl): one file per machine, shared by the main checkout
#     and every worktree, never in a work tree - never in git status, never copied into a sandbox, never one `git add -A`
#     from this PUBLIC repo. Found by READING .git (prove_record's walk), never by running git: inside a hook GIT_DIR is
#     inherited, and git would answer for whichever tree set it. Another PC resolves its OWN common dir.
#   · THE FIRST READ OR WRITE IN A PROCESS FOLDS every checkout's own tv/.second_eye.jsonl in - this checkout's, the main
#     checkout's and every live worktree's (<common>/worktrees/*/gitdir) - deduped by EXACT row and never dropping one: a
#     row a checkout holds N times is held at least N times, and the old files are only READ. After that a checkout's
#     file is read again only when its (size, mtime_ns, inode) moved, so old code still appending to one is folded too.
#   · EVERY APPEND HOLDS THE LEDGER'S LOCK, record()'s and the fold's alike: flock on POSIX; on Windows msvcrt's byte
#     lock on one byte far past the end, so a reader is never refused; with neither, the append runs unlocked and says so.
#   · A TREE WITH NO GIT DIR (a heart2 sandbox, a .git pointer that will not read) keeps its own tv/.second_eye.jsonl,
#     and LEDGER_WHY says why - that file dies with the tree, and the CLI says so.
#   · TV_SECOND_EYE_LEDGER still names a fixture (a law's seam, bound at import); `--gate` ignores it (v2143.1).
# The law: test_the_second_eye_ledger_is_one_per_machine. [[the-unjoined-end]] [[stale-reading]]
MACHINE_NAME = "second_eye.jsonl"
CHECKOUT_NAME = ".second_eye.jsonl"
#: a (size, mtime_ns, inode, device) signature is trusted as a memo key only once the file has been still this long: a
#: coarse clock (ext4 ticks, FAT's two seconds) can give two different writes of one size the same mtime
SETTLE_S = 3.0
#: Windows: the one byte msvcrt locks for an append - far past any real ledger's end, so a reader is never refused
_WIN_LOCK_AT = 1 << 30
_SAID = set()


def _say_once(key, line):
    """A ledger warning, once per process and key, on stderr (stdout is a CLI's verdict)."""
    if key in _SAID:
        return
    _SAID.add(key)
    try:
        sys.stderr.write(line + "\n")
    except Exception:
        pass


def _common_dir(repo):
    """git's COMMON dir for the checkout at `repo`, read from its .git - never by running git. -> (dir, None) | (None, why)"""
    try:
        import prove_record as _pr
        common = _pr._git_common_dir(repo)
    except Exception as e:                        # unreadable is SAID, never guessed
        return None, "its .git could not be read (%s)" % type(e).__name__
    if common:
        return common, None
    if not os.path.lexists(os.path.join(repo, ".git")):
        return None, "this tree has no .git (a sandbox copy, or not a checkout)"
    return None, "its .git pointer does not resolve to a git directory"


def machine_ledger(repo=None):
    """#178 - where this machine's second-eye ledger lives. -> (path, None) | (the checkout's own file, why it is)"""
    repo = os.path.abspath(repo or _ROOT)
    common, why = _common_dir(repo)
    if common:
        return os.path.join(common, MACHINE_NAME), None
    return os.path.join(repo, "tv", CHECKOUT_NAME), why


_WT_ROOTS = {}             # common dir -> (worktrees dir signature, listed at, [worktree roots])


def _worktree_roots(common):
    """Every linked worktree's root, read from <common>/worktrees/*/gitdir. -> [path]. Listed again when the directory
    moved, and at most every 30 s otherwise (a `git worktree move` rewrites a gitdir file, not the directory)."""
    wt = os.path.join(common, "worktrees")
    try:
        st = os.stat(wt)
    except FileNotFoundError:
        return []                                 # no linked worktree was ever made in this repository
    except OSError:
        st = None                                 # could not ask: no cache key - the listing below asks and says why
    key = (st.st_mtime_ns, st.st_ino) if st is not None else None
    hit = _WT_ROOTS.get(common)
    if key is not None and hit is not None and hit[0] == key and time.time() - hit[1] < 30.0:
        return list(hit[2])
    try:
        names = sorted(os.listdir(wt))
    except OSError as e:
        _say_once(("worktrees", common), "second eye: ⚠ the worktree list would not read (%s) - no worktree's own "
                                         "ledger is folded in this time" % type(e).__name__)
        return []
    roots = []
    for n in names:
        try:
            with io.open(os.path.join(wt, n, "gitdir"), encoding="utf-8") as fh:
                p = fh.read().strip()
        except (OSError, ValueError):
            continue                              # a half-made or pruned worktree record: nothing to read
        if p:
            p = p if os.path.isabs(p) else os.path.join(wt, n, p)
            roots.append(os.path.dirname(os.path.normpath(p)))
    _WT_ROOTS[common] = (key, time.time(), roots)
    return list(roots)


def checkout_ledgers(repo=None):
    """#178 - every checkout's OWN ledger on this machine (the pre-#178 layout): this checkout's, the main checkout's and
    every live worktree's tv/.second_eye.jsonl. -> [existing path], one per real file"""
    repo = os.path.abspath(repo or _ROOT)
    found = [os.path.join(repo, "tv", CHECKOUT_NAME)]
    common, _why = _common_dir(repo)
    if common:
        if os.path.basename(common) == ".git":
            found.append(os.path.join(os.path.dirname(common), "tv", CHECKOUT_NAME))     # the main checkout
        for root in _worktree_roots(common):
            found.append(os.path.join(root, "tv", CHECKOUT_NAME))
    out, seen = [], set()
    for p in found:
        r = os.path.realpath(p)
        if r not in seen and os.path.isfile(p):
            seen.add(r)
            out.append(p)
    return out


def _sig(p):
    """(size, mtime_ns, inode, device) of a file, or None when it cannot be stat'ed."""
    try:
        st = os.stat(p)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns, st.st_ino, st.st_dev)


def _settled(sig):
    """Has this file been still for SETTLE_S? Only then may its signature stand for its bytes."""
    return sig is not None and (time.time_ns() - sig[1]) >= SETTLE_S * 1e9


def _read_lines(p):
    """Every non-blank row of a ledger, as the exact bytes written (less the line ending). -> [bytes] ([] if absent)"""
    try:
        with io.open(p, "rb") as fh:
            data = fh.read()
    except FileNotFoundError:
        return []
    return [ln for ln in (x.strip() for x in data.split(b"\n")) if ln]


def _lock(fh):
    """Exclusive lock on a ledger opened for append. -> "flock" | "msvcrt" | None (no lock on this platform)"""
    try:
        import fcntl
    except ImportError:
        fcntl = None
    if fcntl is not None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        return "flock"
    try:
        import msvcrt
    except ImportError:
        return None
    fh.seek(_WIN_LOCK_AT)
    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)    # LK_LOCK retries for about 10 s, then raises
    return "msvcrt"


def _unlock(fh, how):
    try:
        if how == "flock":
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        elif how == "msvcrt":
            import msvcrt
            fh.seek(_WIN_LOCK_AT)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        pass                                      # closing the handle releases it either way


def _append_rows(path, rows, recheck=None):
    """Append whole rows (bytes, no line ending) to the ledger at `path`, under its lock. `recheck(rows_on_disk)` (the
    fold) decides UNDER the lock which rows are still missing. A row a killed writer left without its newline is closed
    first, so it never swallows the next one. -> the rows written"""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with io.open(path, "ab") as fh:
        how = None
        try:
            how = _lock(fh)
        except Exception as e:
            _say_once(("lock-failed", path), "second eye: ⚠ the ledger lock could not be taken (%s) - this append "
                                             "runs without it" % type(e).__name__)
        if how is None:
            _say_once(("no-lock", path), "second eye: ⚠ no file lock on this platform - ledger appends run unlocked")
        try:
            if recheck is not None:
                rows = recheck(_read_lines(path))
            if not rows:
                return []
            data = b"".join(r + b"\n" for r in rows)
            try:
                with io.open(path, "rb") as rd:
                    rd.seek(0, 2)
                    if rd.tell() > 0:
                        rd.seek(-1, 2)
                        if rd.read(1) != b"\n":
                            data = b"\n" + data
            except OSError:
                pass
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
            return list(rows)
        finally:
            _unlock(fh, how)


def _missing(on_disk, sources):
    """The rows of `sources` (lists of rows) the ledger does not hold yet: a row one source holds N times is owed until
    the ledger holds it N times. Ordered by the rows' own clock (`ts`), so a fold keeps the ledger in time order. -> [row]"""
    have = collections.Counter(on_disk)
    out = []
    for rows in sources:
        seen = collections.Counter()
        for r in rows:
            seen[r] += 1
            if seen[r] > have[r]:
                have[r] += 1
                out.append(r)
    keyed, last = [], float("-inf")
    for i, r in enumerate(out):
        t = None
        try:
            d = json.loads(r.decode("utf-8"))
            if isinstance(d, dict) and isinstance(d.get("ts"), (int, float)):
                t = float(d["ts"])
        except Exception:
            t = None
        if t is None:
            t = last                              # a row with no clock stays beside the row before it
        last = max(last, t)
        keyed.append((t, i, r))
    keyed.sort(key=lambda k: (k[0], k[1]))
    return [k[2] for k in keyed]


_FOLDED = {}               # ledger realpath -> {"id": (inode, device), "size": int, "src": {source realpath: signature}}
_FOLD_AT = {}              # ledger realpath -> when this process last asked whether a checkout's ledger moved


def fold(ledger=None, sources=None):
    """#178 - fold every checkout's own ledger into this machine's. -> rows appended (0 when nothing was missing)

    A source is read only when its signature moved since this process last folded it; the rows still missing are
    decided again UNDER the ledger's lock, so two processes folding at once add each row once. Nothing is ever removed,
    from the ledger or from a source."""
    ledger = os.path.abspath(ledger or LEDGER_PATH)
    real = os.path.realpath(ledger)
    if sources is None:
        sources = checkout_ledgers()
    sources = [s for s in sources if os.path.realpath(s) != real]
    lsig = _sig(ledger)
    st = _FOLDED.get(real)
    if st is None or lsig is None or st["id"] != lsig[2:] or lsig[0] < st["size"]:
        st = {"id": lsig[2:] if lsig else None, "size": lsig[0] if lsig else 0, "src": {}}
        _FOLDED[real] = st               # new, replaced or shrunk: every checkout's ledger is read again
    moved = []
    for s in sources:
        ssig = _sig(s)
        if ssig is not None and st["src"].get(os.path.realpath(s)) != ssig:
            moved.append((s, ssig))
    if not moved:
        return 0
    src_rows, readable = [], []
    for s, ssig in moved:
        try:
            src_rows.append(_read_lines(s))
            readable.append((s, ssig))
        except OSError as e:                      # one checkout's unreadable file never blocks the others' rows
            _say_once(("source", os.path.realpath(s), type(e).__name__),
                      "second eye: ⚠ a checkout's own ledger would not read (%s) - not folded this time: %s"
                      % (type(e).__name__, s))
    moved = readable
    wrote = []
    if _missing(_read_lines(ledger), src_rows):
        wrote = _append_rows(ledger, None, recheck=lambda on_disk: _missing(on_disk, src_rows))
    for s, ssig in moved:
        if _settled(ssig):
            st["src"][os.path.realpath(s)] = ssig
    after = _sig(ledger)
    if after is not None:
        st["id"], st["size"] = after[2:], after[0]
    if wrote:
        _say_once(("folded", real, len(wrote), after),
                  "second eye: %d row(s) from %d checkout ledger(s) folded into this machine's ledger (%s)"
                  % (len(wrote), len(moved), ledger))
    return len(wrote)


def _fold_due(path):
    """Before a read or a write of THIS machine's ledger: fold what moved in a checkout's own ledger, asked at most every
    2 s per process. A fixture, a seam's file or a tree with no git dir is never folded into."""
    if LEDGER_WHY is not None or not _MACHINE_LEDGER:
        return
    p = os.path.abspath(path)
    if p != _MACHINE_LEDGER:
        return
    now = time.time()
    if now - _FOLD_AT.get(p, 0.0) < 2.0:
        return
    _FOLD_AT[p] = now
    try:
        fold(p)
    except Exception as e:                        # a fold costs a line, never a read or a write
        _say_once(("fold-failed", p), "second eye: ⚠ the checkouts' own ledgers could not be folded in (%s) - "
                                      "this machine's ledger is read as it stands" % type(e).__name__)


#: #178 - this machine's ledger, and (LEDGER_WHY) why it is this tree's own file instead - None when it is the machine's.
_MACHINE_LEDGER, LEDGER_WHY = machine_ledger()
_MACHINE_LEDGER = os.path.abspath(_MACHINE_LEDGER)
# untracked runtime record of decisions, one per machine; TV_SECOND_EYE_LEDGER names a fixture (bound here, at import)
LEDGER_PATH = os.environ.get("TV_SECOND_EYE_LEDGER") or os.path.abspath(_MACHINE_LEDGER)
# ⚠ NOT FOLDED AT IMPORT. The first READ or WRITE of this machine's ledger in a process folds (_ledger_state, record,
# --gate). Importing alone opens no file under the checkout's own .git/ (audit hook: a main checkout only stats .git; a
# linked worktree reads its .git pointer and its gitdir's commondir, which lie outside its work tree): run_gates' gate
# ledger refuses to carry a gate that read git's own files, and ~36 laws import this module only to drive fixtures -
# folding here would have re-run every one of them on every main-checkout push. console_doctor's direct readers open
# LEDGER_PATH after the push gate (or any earlier read) has already folded it.

# The families that count as a SECOND eye for work authored by Claude. Derived from the model id
# rather than trusted from a caller, because "which family looked at this" is the whole question.
# ⚠ v2145 — TOO NARROW AS WELL AS TOO WIDE. The second eye measured family_of("o3") and
# family_of("mixtral") as None, so two real other-family looks would have been discarded. Matched
# as whole TOKENS of the model id, and the id must LEAD with one (see family_of).
_FAMILY = (
    ("grok", "xai"),
    ("gpt", "openai"), ("o3", "openai"), ("o4", "openai"),
    # v3229 — `codex` denotes OpenAI unambiguously and is how the transport names itself when the
    # answer carries no model header. Without it a real Codex look is UNATTRIBUTABLE and cannot
    # discharge a cross-family debt, which is the lane closing on its own strictness.
    ("codex", "openai"),
    ("gemini", "google"),
    ("llama", "meta"),
    ("mistral", "mistral"), ("mixtral", "mistral"),
    ("deepseek", "deepseek"),
    ("qwen", "qwen"),
    ("command", "cohere"),
    ("claude", "anthropic"),
)

# Who authored a ship when its stamp commit does not say otherwise. A pass from the
# family that stamped THAT version is not a second eye. Grok-seat stamps are xai;
# this name is the fallback, not a claim that every ship was written by Claude.
AUTHOR_FAMILY = "anthropic"

# The Grok code seats that sign a stamp commit. Both are xai: the Grok CLI and Grok Bot's coder seat
# (#230 GB-L). Until v3808 only the CLI spelling was read, so every `Seat: Grok Bot (code)` stamp fell
# back to anthropic and a grok-cli look on it passed as the other family (v3807: grok-cli was its only
# look). A whole line is required, so prose that quotes the seat line decides nothing.
_GROK_SEAT_LINE = re.compile(r"^Seat: Grok (?:CLI|Bot) \(code\)[ \t]*$", re.M)


def _is_grok_seat_message(msg):
    """The commit message carries a Grok code-seat line of its own. -> bool"""
    return bool(_GROK_SEAT_LINE.search(msg or ""))

#: ⚠ THERE IS DELIBERATELY NO MODULE GLOBAL FOR THE SHIP-TABLE VERDICT. v3162 kept
#: LAST_SHIP_TABLE_OK "for older callers" beside the per-call `state` dict; the Codex eye pointed
#: out that any such caller still races, and a grep found ZERO of them repo-wide. Keeping a racy
#: global for callers that do not exist is liability with no benefit — audit(..., state={}) is the
#: only way to learn whether the table was readable. [[the-unjoined-end]]


def family_of(model):
    """anthropic / xai / openai / ... or None when the id does not say ONE recognisable family.

    None is deliberately NOT "some other family" — an unrecognised model cannot be SHOWN to be a
    different one, and [[unknown-stays-unknown]] applies to provenance too.

    ⚠ v2143.1 — AN ADVERSARIAL PASS LAUNDERED CLAUDE AS XAI THROUGH THIS FUNCTION. The first cut
    walked an ordered list of substrings and returned the first hit, with "claude" scanned LAST.
    So `grok-mcp/claude-opus-5` matched "grok" and came back "xai" — the author's own model
    satisfying a gate whose entire purpose is that the author's family does not count. Order can
    never be load-bearing here. Every family is now matched, and:
      · if MORE THAN ONE matches, the id is AMBIGUOUS and returns None. An id naming two families
        cannot be shown to be either one, so it must not buy a pass.
      · a single match returns that family, whichever it is.
    """
    import re as _re
    m = str(model or "").lower()
    toks = [t for t in _re.split(r"[^a-z0-9]+", m) if t]
    if not toks:
        return None
    hits = sorted({fam for needle, fam in _FAMILY if needle in toks})
    if len(hits) != 1:
        return None                       # zero = unrecognised, two+ = ambiguous. Both are UNKNOWN.
    # ⚠ v2145 — AND THE FIRST TOKEN MUST BE THE FAMILY. A substring needle said
    # family_of("not-grok") == "xai": the id says it is NOT grok and the gate read it as grok. The
    # id must LEAD with the family, so "grok-4" qualifies and "not-grok", "fake-grok" and
    # "grok-emulator-by-someone-else" do not. Combined with the ambiguity rule above,
    # "grok-mcp/claude-opus-5" still returns None because two families appear.
    lead = {needle: fam for needle, fam in _FAMILY}.get(toks[0])
    if lead != hits[0]:
        return None
    return hits[0]


def norm_version(v):
    """v2143 — ONE canonical spelling. The writer stored whatever it was handed and the reader
    normalised, so a real cross-family look recorded as "2142" was invisible to `--check v2142`
    while `--audit` cheerfully listed it as OK — two commands, opposite verdicts, and the refusal
    message stating a falsehood. Both ends call this now.
    """
    t = str(v or "").strip().lower()
    if not t:
        return ""
    if t.startswith("v"):
        t = t[1:]
    return ("v" + t) if t.isdigit() else ""


def current_version(here=None):
    """The version the four stamps agree on, read from the JSON one (the only machine-readable one)."""
    p = os.path.join(here or HERE, "WINDOWS_SHIP.json")
    try:
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        # "ver" is the real key in WINDOWS_SHIP.json — measured, not guessed. The others are kept
        # as fallbacks, but an unrecognised shape returns None and the CLI treats that as UNKNOWN
        # rather than as a pass.
        for k in ("ver", "version", "ship", "build", "v"):
            v = d.get(k)
            if isinstance(v, str) and re.match(r"^v?\d+$", v.strip()):
                return v.strip() if v.strip().startswith("v") else "v" + v.strip()
    except Exception:
        pass
    return None


def _parse_ledger(p):
    """Every row of the ledger at `p`, in file order. Raises when the file cannot be read."""
    out = []
    with io.open(p, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue          # one bad line must not blind the whole ledger
            if isinstance(row, dict):
                out.append(row)   # ...and a line that PARSES but is not an object is one of
                                  # those bad lines. It used to reach every consumer and
                                  # traceback --audit, which is the recovery command the
                                  # refusal message tells him to run.
    return out


# ══ #48 (REG-2453) — ONE PARSE PER LEDGER STATE, NOT ONE PER QUESTION ══════════════════════════════════════════════
# MEASURED 2026-10-22 on a COPY of his 7.3 MB, 2,274-row ledger: console_doctor's "second eye asked twice" row asks
# current_version, agreement(v) and agreement_census() - and the census asks agreement() once per recent version, each of
# which re-read and re-parsed the WHOLE file: 43 parses, 3.4 of the census's 3.96 s (profiled; 6-10 s under a loaded
# Mac). The parse is now kept per (path, size, mtime_ns, inode, device): a ledger that did not move is parsed once per
# process, a row appended is a new signature and is seen on the next read, and a file written in the last SETTLE_S is
# never memoised (its signature cannot yet stand for its bytes). The census is kept per (state, recent) - and only while
# the readers it is built from are this module's own (a law that swaps _rows or agreement gets a fresh census). Every
# caller gets COPIES: a census deep-copied, each row a shallow copy - so a reader that sets a row's key can never edit
# the memo, and one that edited a NESTED value (a findings list in place) would. None does: every public reader here and
# 22 console_doctor rows (every one named for the eye or a ledger) left a kept parse deep-equal (measured 2026-10-22).
# The law: test_the_second_eye_row_reads_the_ledger_once.
_PARSED = {}               # abspath -> {"sig": signature, "rows": [row]}
_CENSUS = {}               # (abspath, recent) -> (signature, census)


def _ledger_state(path=None):
    """The parsed ledger at `path` (default LEDGER_PATH, read at call time). -> {"sig", "rows"} | None (unreadable)"""
    p = os.path.abspath(path or LEDGER_PATH)
    _fold_due(p)
    sig = _sig(p)
    if sig is None:
        return None
    hit = _PARSED.get(p)
    if hit is not None and hit["sig"] == sig:
        return hit
    try:
        rows = _parse_ledger(p)
    except Exception:
        return None
    state = {"sig": sig, "rows": rows}
    if _settled(sig) and _sig(p) == sig:
        _PARSED[p] = state
    else:
        _PARSED.pop(p, None)
    return state


def _rows(path=None):
    st = _ledger_state(path)
    if st is None:
        return []
    return [dict(r) for r in st["rows"]]



def _bytes_seen(path=None):
    """-> {'bible': '<sha1-12>', 'at': <mtime>} for the file a look was taken against, or None.

    None means NOBODY RECORDED IT, which is a different fact from a hash that does not match, and
    the audit below must keep them apart. Every row written before v2708 has None here on purpose:
    backfilling a plausible hash would forge exactly the evidence this field exists to supply.
    """
    p = path or os.path.join(os.path.dirname(HERE), "bible.html")
    try:
        import hashlib
        h = hashlib.sha1()
        with io.open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return {"bible": h.hexdigest()[:12], "at": int(os.path.getmtime(p))}
    except Exception:
        return None


# ── ⚠⚠ WAS THE CODE ACTUALLY SENT? ──────────────────────────────────────────────────────────
# 2026-09-08. Four "cold code reviews" in one session were recorded as reached=True looks, and in
# every one of them the code fence contained the LITERAL text
#
#     """ + open('/tmp/eye_cold.txt').read() + """
#
# because the prompt was assembled as a plain string and the concatenation was never evaluated. The
# model received a fence full of Python source-expression and several paragraphs of careful prose
# context — and answered CONFIDENTLY, in specific-sounding language ("the inference is unsound under
# the documented threading model"), about code it had never seen. Nothing in the lane could tell the
# difference, because the ledger recorded the CLAIM that a look happened and never the TRANSMISSION.
# A sentinel probe settled it: asked to quote the first line of the snippet, the model answered
# "NO CODE RECEIVED".
#
# ⚠ It was NOT all of them — v2775's prompt carried its diff intact and its finding (a redundant
# `max-width: 100%`) was real and was acted on. That is the point: a blanket retraction would have
# been as unmeasured as the original claim. Grep the stored prompt, count the literals, and let the
# count decide. [[unknown-stays-unknown]] [[silence-is-not-evidence]] [[the-unjoined-end]]
# ⚠⚠ v3403 — A VERDICT THAT SAYS "I COULD NOT JUDGE THIS" IS NOT A LOOK.
# MEASURED 2026-09-20 across all 915 rows: `cannot-tell` appears 20 times over 20 versions, and
# for ELEVEN of them it is the ONLY qualifying row. Eight of those eleven were answering "looked
# at" to the ship gate — v2415, v2665, v3346, v3355, v3357, v3358, v3359, v3401 — on the strength
# of an eye that had said, in its own words, that the payload did not carry enough of the change
# to judge. (The other three were already refused for unrelated reasons, which is how we know the
# refusal path works and this is a VERDICT-SEMANTICS hole rather than a broken reader.)
#
# looked_at() applied exactly three tests — reached, cross-family, bound to evidence — and never
# asked what the verdict MEANT. So three states (clean / found-things / COULD-NOT-REVIEW) were
# collapsed into two, which is this codebase's most repeated defect wearing the ledger's clothes.
# [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
#
# ⚠ THE ROW IS STILL RECORDED. It is evidence about REACH (task #143) and must never be deleted
# or downgraded to an empty seat — an articulate refusal is MORE informative than a terse pass,
# it simply is not agreement.
# ⚠ AND THIS PINS ONE WORD ON PURPOSE. Refusing every unrecognised verdict would be an off switch
# that reads as rigour: the ledger carries nine other free-text phrasings in live use
# (confirmed-fix, two-real-one-refuted, clean-for-the-shipped-change, ...) and they must keep
# counting. [[strictness-that-closes-the-lane]]
_NOT_A_LOOK = ("cannot-tell",)


def is_not_a_look(verdict):
    """True when the eye answered that it COULD NOT judge. -> bool"""
    return str(verdict or "").strip().lower() in _NOT_A_LOOK


#: the prefix second_eye_run gives the eye's own "what I was not shown" line when it files it among the findings
NOT_SHOWN_PREFIX = "NOT SHOWN (the eye's own words): "


def a_template_not_a_look(row):
    """REG-2740 - the eye was held to the verdict schema, answered verdict "findings" and listed NONE. -> bool

    MEASURED on v3820's row: {"verdict":"findings","findings":[],"unseen":"placeholder"} - the schema filled in, a
    placeholder where the reach note goes. The runner filed the unseen note among the findings, so the row carried one
    line, `_has_evidence` read that line as a finding, and the push gate let v3821 ship past a seat nobody sat in.
    A schema verdict of findings with nothing but the eye's own NOT SHOWN note contradicts itself: it is not a look.
    ⚠ ONLY schema rows. 92 rows drained from public #231 comments also say findings and list none, and every one of
    them is bound to the comment that carries its findings (verdictFrom "gh#231 comment <id>") - those are looks."""
    if not isinstance(row, dict) or str(row.get("verdictFrom") or "").strip() != "schema":
        return False
    if str(row.get("verdict") or "").strip().lower() != "findings":
        return False
    lines = [str(f or "").strip() for f in (row.get("findings") or []) if str(f or "").strip()]
    return all(f.startswith(NOT_SHOWN_PREFIX) or not_a_finding(f) for f in lines)


#: REG-2770 (v3825's row) - a word the schema's slot was filled with, not a defect
_FILLER = re.compile(r"^(placeholder|pending|tbd|todo|n/?a|none|nothing|\.\.\.|-)[.!]?$", re.I)
#: REG-2770 - an announcement of what the eye meant to read next, not a finding about what it read
_INTENT = re.compile(r"^(i need (the|to read|to see|more)|i will (read|look|open|check)|i'll (read|look|open|check)|"
                     r"let me (read|look|open|check)|reading the |i am going to (read|look|open))", re.I)
#: REG-2777 (the v3827 second eye) - a clause that says what goes WRONG. After an intent opener it makes the sentence a
#: finding ("Reading the lock-heart shows the span is never closed, so the session stays pinned."), not a plan to read
_CONSEQUENCE = re.compile(r"(,\s*(so|or|which|otherwise)\b|\b(never|keeps?|stays?|fails?|breaks?|leaks?|stale|wrong|drops?|"
                          r"loses?|raises?|crash(es)?)\b)", re.I)


def _only_intent(t):
    """REG-2777 - every sentence of the line announces what the eye means to read, and none says what goes wrong. The
    opener alone used to decide, so a defect phrased after "I need the" or "Reading the" was dropped as a plan. -> bool"""
    ss = [x for x in re.split(r"(?<=[.!?])\s+", t) if x.strip()]
    return bool(ss) and all(_INTENT.match(x) and not _CONSEQUENCE.search(x) for x in ss)


def not_a_finding(line):
    """REG-2770 - MEASURED on v3825's row: the eye answered verdict "findings" with three lines - "placeholder", "I need the
    surrounding functions before naming a failure scenario. Reading the lock-heart and session-span code that the diff
    cuts off." and its NOT SHOWN note "pending". REG-2740 refused a row of NOT SHOWN notes only, so this one counted as a
    look with 3 findings while it named no defect. A line that is only a filler word, or only announces what the eye
    means to read, is not a finding. -> bool"""
    t = str(line or "").strip()
    return bool(_FILLER.match(t) or _only_intent(t))


def row_is_not_a_look(row):
    """The ONE answer to "does this reached, cross-family, evidenced row fail to count as a look?" - read by looked_at,
    audit() and the gate's refusal message alike, so no surface can read a row another way (v3415). -> bool"""
    return is_not_a_look((row or {}).get("verdict")) or a_template_not_a_look(row)


_UNSENT_MARKERS = (
    # a file-reading expression that survived into the prompt instead of being evaluated
    (re.compile(r"open\s*\(\s*['\"][^'\"]*['\"]\s*\)\s*\.\s*read\s*\(\s*\)"),
     "an un-evaluated open(...).read() reached the prompt as text"),
    # The concatenation seam either side of it.
    #
    # ⚠ v2808 — THESE TWO LET `\s*` CROSS A NEWLINE, AND EVERY CODE REVIEW IS A UNIFIED DIFF.
    # In a diff every added line begins with `+`, so an added docstring renders as `+"""` and a
    # docstring followed by an added line renders as `"""\n+import os`. Both matched. Measured on
    # the v2807 payload: 24 hits, ALL of them ordinary Python docstrings beside a diff marker, and
    # ZERO real open().read() seams. Because a non-empty `unsent` RETRACTS the row, this would
    # have marked every future code review an EMPTY SEAT — and since a version cannot ship while
    # the previous one has never been looked at, the ledger would have deadlocked the repo shut.
    #
    # It stayed invisible only because sentCode was measuring a dict and returning 0 fences; the
    # moment that was fixed, this fired. Two defects where the first was hiding the second.
    # [[two-fixes-broke-each-other]] [[feedback-suspect-the-instrument]]
    #
    # A REAL seam is `""" + x` or `x + """` on ONE line. `[ \t]` cannot cross a newline, and the
    # leading `\S` refuses a `+` that begins its line — which is exactly what a diff marker is.
    #
    # ⚠⚠ v2824 — AND THE QUOTES MUST BE THE **SAME** QUOTE THREE TIMES. `["\']{3}` matches any
    # three quote CHARACTERS, so ordinary JavaScript string concatenation of a quote —
    # `esc(call) + \'"\'` — read as a Python triple-quote seam. Measured on the v2821 review
    # payload: ONE hit, and it was `+ \'"\'` in a diff of bible.html. Because a non-empty `unsent`
    # RETRACTS the row, every future review of a diff touching control_ui.html or bible.html would
    # have filed as an EMPTY SEAT — and a version cannot ship while the previous one has never
    # been looked at, so the ledger would have deadlocked the repo shut.
    #
    # ★ THAT IS THE SAME DEADLOCK v2808 FIXED, IN A DIFFERENT SPELLING. The note above says it in
    # as many words. The narrowing was applied to WHERE the pattern may match (not across a
    # newline, not on a diff marker) and never to WHAT a triple quote actually is. A guard hardened
    # against one spelling of its own false positive is hardened against that spelling only.
    # [[feedback-suspect-the-instrument]] [[sabotage-is-usually-the-wrong-one]]
    (re.compile(r"(?:\'{3}|\"{3})[ \t]*\+"), "a triple-quote/+ concatenation seam reached the prompt as text"),
    (re.compile(r"\S[ \t]*\+[ \t]*(?:\'{3}|\"{3})"), "a +/triple-quote concatenation seam reached the prompt as text"),
)

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)

#: How many LINES OF CODE a fence must carry before an un-evaluated-expression marker inside it is
#: treated as a coincidence of text rather than a promise standing in for a file.
#:
#: ⚠⚠ v2842 — THIS WAS A CHARACTER COUNT AND A CROSS-FAMILY REVIEW BROKE IT IN ONE TRY. Padding a
#: fence with 30 lines of prose puts it over any character floor while it still carries ONE line of
#: code — I built the counter-example and measured it: 2,409 chars, SLIPPED THROUGH. Size is not
#: the property; the property is whether the fence actually carries code, and prose does not add
#: code lines. Measured on the same pair: the padded promise has 1 code line, a real review payload
#: has 69. [[zero-needs-a-denominator]]
_PROMISE_MIN_CODE_LINES = 8

#: Kept only for the `chars` field the ledger reports. It is NOT the test any more.
#: ⚠ THE RETIRED CHARACTER FLOOR. v2842 replaced it with `_PROMISE_MIN_CODE_LINES` because a fence
#: padded with thirty lines of prose clears any character floor while carrying ONE line of code.
#: It is kept — and RENAMED from `_PROMISE_MAX_CHARS` — because a law still asserts that its
#: counter-example fixture clears the old floor, which is what makes that fixture a proof that the
#: hole was real rather than a fixture that merely passes. Nothing in this module reads it.
#: The old name claimed a rule this file no longer applies; a right number under a word that
#: stopped being true is the defect caught here more than any other. [[label-outlived-referent]]
_RETIRED_CHAR_FLOOR = 2000


def _code_lines(body):
    """Lines in a fence that are neither blank nor a comment. -> int

    The discriminator between a payload and a padded promise: prose and blank lines are free to add
    and add nothing here.
    """
    n = 0
    for line in str(body or "").split("\n"):
        t = line.strip()
        # a unified diff prefixes every line; strip it before asking whether it is a comment
        if t[:1] in "+-" and len(t) > 1:
            t = t[1:].strip()
        if t and not t.startswith("#"):
            n += 1
    return n

#: A Python comment line, with an optional unified-diff marker in front of it. Prose about a rule
#: is not the rule — the distinction this repo has paid for more than once.
_COMMENT_LINE = re.compile(r"^[-+ ]?\s*#")


def code_was_transmitted(sent):
    """Did the prompt actually CARRY code, or only a promise of it? -> dict

    Returns {"chars": int, "fences": int, "unsent": [why, ...]}. `chars` counts characters inside
    fenced blocks only, so prose describing code does not read as code. An empty `unsent` list with
    `chars == 0` is a different fact from `unsent` being non-empty: the first means no fence at all
    (maybe a pixel look, maybe a question), the second means a fence that was meant to hold code and
    holds an expression instead.
    """
    t = str(sent or "")
    fences = _FENCE_RE.findall(t)
    chars = sum(len(f) for f in fences)
    why = []
    # ⚠ SEARCH THE FENCES, NOT THE WHOLE PROMPT. A prompt may legitimately DISCUSS open().read() in
    # its prose — this very docstring would trip a whole-text search. The defect is a fence that was
    # supposed to hold the file and holds the expression that would have read it.
    for body in fences:
        # ⚠⚠ v2825 — SKIP COMMENT LINES, BECAUSE THE GUARD MATCHED ITS OWN DOCUMENTATION.
        # The comment beside `_UNSENT_MARKERS` reads: "A REAL seam is `\"\"\" + x` or `x + \"\"\"`
        # on ONE line" — and when a review diff includes second_eye_ledger.py ITSELF, that sentence
        # is inside the fence and BOTH markers fire on it. The row is retracted, the look files as
        # an empty seat, and the next push is refused. Measured on the v2824 payload: two hits,
        # both on that one comment line, zero real seams.
        #
        # ★ THE DOCSTRING ABOVE ALREADY NAMES THIS DEFECT ONE LEVEL UP — "a prompt may legitimately
        # DISCUSS open().read() in its prose... the defect is a FENCE that was supposed to hold the
        # file and holds the expression instead" — and the fix was to search fences not prose. When
        # the fence holds a real file whose PROSE discusses the pattern, the same problem returns
        # inside it. A rule and a sentence describing the rule are different things at every depth.
        # [[feedback-comments-vs-code]] [[source-reading-guard]]
        #
        # ⚠ The leading `[-+ ]?` is the diff marker: inside a unified diff a comment line reads as
        # `+    # ...` or `     # ...`, so the `#` is not the first non-space character.
        _code = "\n".join(ln for ln in body.split("\n")
                          if not _COMMENT_LINE.match(ln))
        # ⚠⚠ v2840 — A MARKER ONLY MEANS SOMETHING WHILE THE FENCE COULD *BE* THE PROMISE.
        # These markers exist to catch a prompt whose fence holds an un-evaluated expression
        # INSTEAD OF the file. A fence carrying thousands of characters of real diff manifestly
        # holds the code, and a stray textual match inside it is noise — twice now it has retracted
        # a genuine look:
        #   v2825  matched this file's own COMMENT describing what a seam looks like
        #   v2840  matched `open("control_app.py").read()` inside a STRING LITERAL that is test
        #          fixture data — in 14,777 characters of transmitted diff
        # Each retraction files the look as an EMPTY SEAT, and a version cannot ship while the
        # previous one has never been looked at, so each one blocks the repo.
        #
        # The size IS the evidence. Below the floor the expression could plausibly be the whole
        # payload; above it the code is present whatever the text also happens to say.
        # [[feedback-comments-vs-code]] [[zero-needs-a-denominator]]
        if _code_lines(body) >= _PROMISE_MIN_CODE_LINES:
            continue
        for rx, msg in _UNSENT_MARKERS:
            if rx.search(_code) and msg not in why:
                why.append(msg)
    return {"chars": int(chars), "fences": len(fences), "unsent": why}


def record(version, model, verdict, findings=None, images=None, asked=None,
           answer_head=None, reached=True, path=None, seen_path=None, sent=None, sha=None,
           head_cap=None, absent=None, absent_kinds=None, reach=None, stripped=None,
           verdict_from=None):
    """Append one look. Returns the row written.

    `verdict` is what the OTHER family concluded: "clean" | "findings" | "cannot-tell".
    `reached` False means the seat was empty — the row is still written, on purpose, so a run of
    failures is visible instead of looking like nobody tried.

    ⚠ `sent` is the FULL PROMPT TEXT that went to the other family. Pass it whenever the look was a
    CODE review. If its fences carry an un-evaluated file-read expression instead of the file, the
    row is forced to reached=False and retracted here rather than being believed — see
    `code_was_transmitted`. Omitting `sent` records None, which means NOBODY CHECKED, not "fine".
    """
    # ⚠ v2808 — THE CALLER AND THIS LINE DISAGREED ABOUT WHAT `sent` IS, AND THE FIELD READ 0
    # FOR EVERY PRODUCTION LOOK. second_eye_run computes `sent = code_was_transmitted(prompt)` —
    # already a measurement — and this re-measured that DICT, which carries no code fence. So it
    # returned {"chars": 0, "fences": 0}: byte-identical to what `sent=None` produces. A row that
    # says "nobody passed the prompt in" and a row that says "the whole diff was sent" became the
    # same row, in the one field built to stop a thin look being filed as a thorough one.
    #
    # MEASURED across the ledger: 417 rows, 20 carrying a sentCode, 9 of them ZERO — every look
    # taken through the real path — and the 11 healthy ones all written by the TEST, which passes
    # a raw fence. The gate was green because it exercised a shape production never uses.
    # [[feedback-blind-fixture-green-gate]] [[gate-blind-to-unexercised-input]]
    if sent is None:
        _sent = None
    elif isinstance(sent, dict):
        # already measured by the caller — trust it, but only if it has the shape
        _sent = ({"chars": int(sent.get("chars") or 0),
                  "fences": int(sent.get("fences") or 0),
                  "unsent": list(sent.get("unsent") or [])}
                 if ("chars" in sent) else None)
    elif isinstance(sent, str):
        _sent = code_was_transmitted(sent)
    else:
        # ⚠ NOT a silent zero. An unrecognised type is an absence of measurement, and absence is
        # None here — the one value this field defines as "nobody checked". [[unknown-stays-unknown]]
        _sent = None
    if _sent and _sent["unsent"]:
        reached = False
        verdict = "cannot-tell"
    # ⚠⚠ `or`, NOT `if head_cap is None` — AND A SECOND EYE ASKED FOR THE OPPOSITE. It read
    # `head_cap=0` silently becoming 600 as a defect. It is the correct behaviour, and MEASURED
    # here: a non-positive cap is meaningless for a HEAD field (storing nothing is not a cap), so
    # falling back to the default is the only sensible answer.
    # ⚠ AND THE "FIX" WOULD CREATE A REAL ONE. The same review also flagged that a row whose
    # headCap is 0 lands in prefixOnly regardless of length. Today that is UNREACHABLE precisely
    # because this `or` means record() can never WRITE a 0. Make 0 stay 0 and the second finding
    # becomes live. The two findings are in tension; the safe pair is the one already here.
    # Verified: head_cap=0 -> headCap=600, and a hand-written headCap=0 row with a non-empty head
    # does land in prefixOnly. [[sabotage-is-usually-the-wrong-one]]
    _cap = int(head_cap or ANSWER_HEAD_CAP)
    # v3386 (#129) — THE ROW KEPT THE VERDICT AND THREW AWAY THE EVIDENCE.
    # `answerHead` is a PREFIX. MEASURED over 898 rows: 876 carry a head, median 400 chars, max
    # 600 — the cap. The text past it was never stored anywhere, so NO parser change could ever
    # be validated against history and a re-judge was impossible BY CONSTRUCTION, not by
    # accident. That is the exact shape [[heart-first]] §6 exists for: an engine that computes
    # rich information, writes a lossy summary, and leaves the next stage unable to ask a
    # question the store can no longer answer.
    #
    # ⚠ THE CALLER ALREADY HANDS THE WHOLE ANSWER OVER. v3339 moved the cut out of the runner
    # into this one place, so `answer_head` arrives COMPLETE and was being discarded here. The
    # fix is to keep what was already in hand, not to fetch anything new.
    #
    # ⚠ `answerChars` IS THE TRUE LENGTH, always, so neither stored field can lie about being
    # whole: answerChars > len(answerFull) means even the full field was cut.
    _raw = str(answer_head or "")
    row = {
        "version": norm_version(version) or str(version or "").strip(),
        # ⚠⚠ v3316 — WHICH COMMIT WAS ACTUALLY READ. `payload_for(sha)` resolves a commit, builds
        # the diff from it, and the sha was then THROWN AWAY: across all 824 rows written before
        # this, there is no sha key at all. So the ledger could answer "was this VERSION looked
        # at" and could not answer "was this COMMIT looked at" — and the second question is the
        # one that matters, because this repo batches 3-4 versions per commit on purpose.
        #
        # MEASURED 2026-09-18: `0bf8cb6d` is titled "v3304-v3307" and ships FOUR versions. Asking
        # the eye once per version would have sent the SAME 10,016-byte payload four times — four
        # paid looks at one set of bytes, filed as four independent reviews. That is n inflated by
        # repetition, which is fake confluence, and it is the error this field exists to prevent.
        # One look, one sha, credited to every version that commit shipped.
        # [[heart-first]] §6 — persist what you KNEW, not a summary of it.
        "sha": (str(sha).strip() or None) if sha else None,
        "ts": int(time.time() * 1000),
        "model": str(model or ""),
        "family": family_of(model),
        "reached": bool(reached),
        # ⚠⚠ v3349 — WHICH CHANGED FILES NEVER REACHED THE EYE, AS A LIST. payload_for() has
        # computed this since v3341 and used it to WARN THE EYE inside the prompt; the ROW only
        # ever got it as a 400-char-capped prose suffix on `asked`, so no reader could tell a
        # complete look from a blind one. MEASURED on v3347: the payload cut 8,967 of 92,115 diff
        # chars and dropped 10 files INCLUDING tv/self_arming.py, the one the version exists to
        # change; the eye answered "all other listed files UNKNOWN"; the row said verdict=clean.
        #
        # ⚠ THREE STATES, KEPT APART, and the middle one is the whole point:
        #     [...]  measured, and these files are missing
        #     []     measured, and nothing is missing
        #     null   nobody could ask — which is also what a MISSING key means, i.e. every row
        #            written before this version
        # Collapsing null into [] would turn "we never checked" into "we checked and it was fine",
        # which is the confident zero this repo keeps re-learning to distrust.
        # ⚠ `reached` answers a DIFFERENT question and is not a substitute: it means the SEAT
        # ANSWERED. A reachable eye handed two hunks of a twelve-file change is reached=True and
        # blind, which is exactly the v3347 row.
        # [[one-to-one-store-for-a-one-to-many-fact]] [[unknown-stays-unknown]] [[the-unjoined-end]]
        "absent": (list(absent) if absent is not None else None),
        # v3363 - AND HOW MUCH OF EACH FILE THAT *DID* ARRIVE. `absent` is answered by the
        # presence of a `diff --git` header; truncation cuts MID-FILE, so a file whose header
        # arrived and whose body was chopped is absent-clean and unread. MEASURED over 12
        # versions: 8 of 67 ARRIVED files came in under half their bytes, and one of them was
        # tv/second_eye_ledger.py on v3354 at 48.6% - the file that version exists to change,
        # filed blind_to [] and verdict clean.
        # ⚠ THE FRACTION, NEVER A FLAG. got/total per file keeps the bar in the READER where it
        # can be moved; a bool here would bake in a number nobody measured.
        # ⚠ None means nobody could measure. [[unknown-stays-unknown]]
        "reach": (dict(reach) if isinstance(reach, dict) else None),
        # ⚠⚠ v3375 — AND HOW MUCH OF THE AUTHOR'S OWN ACCOUNT WAS REMOVED BEFORE THE EYE SAW
        # IT: {"comments": n, "notes": n}, in characters. payload_for strips comment-only added
        # lines and (in run_gates.py) `why=` ship notes, and until v3375 it told NOBODY — not the
        # eye in the prompt, not the ledger in the row. MEASURED on v3374: notes 7,885 chars, 22%
        # of the raw diff; over 39 version commits the comment strip fired 39/39 and the ship-note
        # strip 22/39. The cost showed up in v3374's own look, which reported a claim-versus-
        # delivery finding invented from a docstring because the author's real note had been
        # replaced by a stub.
        # ⚠ null is NOBODY MEASURED — every row written before this version — and is never 0.
        # A dict with a 0 in it means MEASURED AND NOTHING WAS STRIPPED, which is a different
        # fact and the one that lets a reader trust the look. [[unknown-stays-unknown]]
        "stripped": (dict(stripped) if isinstance(stripped, dict) else None),
        # ⚠⚠ v3354 — WHAT KIND OF CHANGE EACH ABSENT FILE CARRIED: {path: stamp|substantive|
        # unknown}. `absent` alone cannot say whether a look missed anything a reviewer could have
        # held an opinion about, because bible.html and tv/tv_diablo.py are absent from almost
        # every payload while carrying two lines of version stamp — so the v3349 warning built on
        # it fired on 7 of 7 rows where the honest count was 2. The classification is knowable the
        # moment the row is written; persisting it is free and re-deriving it costs a git call per
        # file, per read. [[heart-first]] §6 — persist what you KNEW, not a summary of it.
        # ⚠ THREE STATES, matching `absent` exactly: a dict means measured, {} means measured and
        # nothing was missing, null means reach was never established — which is every one of the
        # 867 rows before this version. Those are measured ON READ from their own sha rather than
        # assumed to be stamps; assuming would be the confident zero this field exists to refuse.
        "absentKind": _kinds_for(absent, absent_kinds, sha),
        "verdict": str(verdict or ""),
        # ⚠⚠ v3420 — HOW THE VERDICT WAS OBTAINED, BECAUSE THE TWO ROUTES ARE NOT THE SAME
        # EVIDENCE. "schema" means the transport CONSTRAINED the model to an enum and this field
        # was read. "prose" means a regex inferred it from sentences — the route whose own
        # docstrings in second_eye_run.py record a CLEAN look filed as `findings`, a fix that was
        # "wrong in BOTH directions", and a review filed `findings` because the word after
        # `defects` was `meeting`. A reader that cannot tell them apart cannot weight them apart.
        #
        # ⚠ THREE STATES: "schema" · "prose" · null. null is every row written before this
        # version — nobody recorded how it was obtained, which is NOT the same as prose.
        # [[unknown-stays-unknown]]
        "verdictFrom": (str(verdict_from).strip() or None) if verdict_from else None,
        "findings": list(findings or []),
        "images": [os.path.basename(str(i)) for i in (images or [])],
        "asked": (str(asked or "")[:400]) or None,
        # the head of the RAW answer, so a plausible-sounding summary cannot stand in for a look
        # ⚠⚠ v3339 (#77) — ONE TRUNCATION, AND THE ROW REMEMBERS THE CAP. The cap used to be
        # written in FOUR places: this line plus three slices in second_eye_run (400 on the
        # reached path, 200 on each unreached one). The runner cut FIRST, so a row capped at 400
        # never reached 600 and verdict_provenance re-judged it as if the whole answer were there.
        # MEASURED on 843 rows: 381 sit at 400 and prefixOnly reported 98 where the honest figure
        # is 479 — and the census, counting only this 600, said 91. Two readings disagreeing
        # because one number lived in four places. [[copy-drift]] [[heart-first]] §6 — persist what
        # you knew, not a summary of it.
        # ⚠ `head_cap` is resolved HERE, not in the signature: ANSWER_HEAD_CAP is defined further
        # down this file, and a default evaluated at import time freezes whatever the bar was the
        # day the line was written. [[regression-guard]] §4
        "answerHead": (_raw[:_cap]) or None,
        # v3386 — THE WHOLE ANSWER, so a re-judge is possible at all. Rows written before this
        # version carry no answerFull and a reader must treat them as UNKNOWN rather than
        # assuming the head was everything. [[unknown-stays-unknown]]
        "answerFull": (_raw[:FULL_ANSWER_CAP]) or None,
        # the TRUE length of what the eye said, independent of either cap
        "answerChars": len(_raw),
        "fullCap": FULL_ANSWER_CAP,
        # what that head was cut to, so a reader never has to guess which cap applied
        "headCap": _cap,
        # v3315 — WHICH GENERATION OF THE PARSER REACHED THIS VERDICT. 824 rows were written
        # without it, and 64 of those carry a verdict their own stored answer contradicts.
        "judgedBy": PARSER_GEN,
        # ⚠⚠ WHAT WAS ACTUALLY PHOTOGRAPHED. Until this existed, a look was bound to a version
        # NUMBER and to nothing else, so "was v2694 looked at" could only ever be answered from a
        # label somebody typed. MEASURED over all 343 rows: SIXTEEN looks are credited to more
        # than one version — 40 version rows resting on 16 actual looks, the widest being ONE look
        # credited to five (v2205-v2209) and another to four (v2685-v2688). `--audit` prints
        # `OK vNNNN looks=1` for every one of them.
        #
        # That is not automatically dishonest: versions are batched 3-4 per push on purpose, and
        # one look at the final pixels of a batch legitimately covers every version IN it. What it
        # cannot distinguish is a FORWARD credit — a look at bytes that did not yet contain the
        # change being credited. I tried to settle that from timestamps and it does not work: my
        # own v2697 row "predates its commit" because I rendered the working tree, had it looked
        # at, then committed. Clock order cannot tell a working-tree look from a forward credit.
        #
        # A hash can. Recording what the photographed file actually hashed to turns "did this look
        # see version X" from an inference into a comparison. [[unknown-stays-unknown]]
        # ⚠ v2712 — THE FIELD COULD NOT BE TOLD WHAT WAS PHOTOGRAPHED. `_bytes_seen()` already
        # took a path; `record()` never passed one, so every row hashed the WORKING TREE whatever
        # the look was actually taken against. That defeats the field's own stated purpose — it
        # exists to turn "did this look see version X" from an inference into a comparison, and a
        # hash of a file the eye never saw is an inference wearing a measurement's clothes.
        # Surfaced by needing to look at origin/main's bible.html, which is exactly the case the
        # field was built for. [[unknown-stays-unknown]]
        "bytes": _bytes_seen(seen_path),
        # what the other family was actually HANDED. None = nobody passed the prompt in, which is
        # an absence of measurement and never a pass. [[unknown-stays-unknown]]
        "sentCode": _sent,
    }
    if _sent and _sent["unsent"]:
        row["retracted"] = ("the prompt's code fence carried no code — " +
                            "; ".join(_sent["unsent"]) +
                            ". Recorded as an EMPTY SEAT: the model answered about code it never "
                            "received.")
        row["claimedVerdict"] = str(verdict or "")
    p = path or LEDGER_PATH
    # #178 (REG-2450) - into THIS machine's ledger, after what a checkout's own ledger still held, under the lock
    _fold_due(p)
    _append_rows(p, [json.dumps(row, ensure_ascii=False).encode("utf-8")])
    return row


def _has_evidence(row):
    """Is this row bound to anything a person could go and check?

    Any ONE of: the head of the raw answer, a named image, or a finding the other family made.
    Empty strings do not count in any of them — measured: images:[""] satisfied the first cut.
    """
    if str(row.get("answerHead") or "").strip():
        return True
    if any(str(i or "").strip() for i in (row.get("images") or [])):
        return True
    if any(str(f or "").strip() for f in (row.get("findings") or [])):
        return True
    # v3553 - A LOOK DRAINED FROM A PUBLIC COMMENT IS BOUND TO THAT COMMENT. Anyone can open `gh#231 comment <id>` and
    # read the seat's whole judgement there; until v3553 the drain stored no words for a CLEAN look, so every clean
    # #231 verdict sat in the ledger counted as nothing. A row with neither words nor a comment still does not count.
    if _COMMENT_REF_RX.match(str(row.get("verdictFrom") or "").strip()):
        return True
    return False


#: a drained row names the public comment it copies, e.g. "gh#231 comment 5940881185"
_COMMENT_REF_RX = re.compile(r"^gh#\d+ comment \d+$")


def _commit_is_grok_seat(sha, version, repo=None):
    """The named commit carries the Grok code-seat line, and its stamp is this version.

    A comment that merely SAYS the author was Grok is not evidence. The commit is.
    """
    sha = str(sha or "").strip()
    ver = norm_version(version)
    if not sha or not ver:
        return False
    try:
        msg = subprocess.run(
            ["git", "show", "-s", "--format=%B", sha],
            cwd=(repo or _REPO), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15)
        if msg.returncode != 0 or not _is_grok_seat_message(msg.stdout):
            return False
        ship = subprocess.run(
            ["git", "show", "%s:tv/WINDOWS_SHIP.json" % sha],
            cwd=(repo or _REPO), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15)
        if ship.returncode != 0:
            return False
        return norm_version(json.loads(ship.stdout or "").get("ver")) == ver
    except Exception:
        return False


def _claude_looked_at_a_grok_seat(row, repo=None):
    """family_of cannot name this model line: it says Claude and it says Grok.

    The #231 seat writes that when it reviewed a Grok-authored ship. The looking
    family is the leading word. Who wrote the ship is the commit, not the parenthesis.
    """
    model = str((row or {}).get("model") or "").strip().lower()
    if not model.startswith("claude") or "author seat was grok" not in model:
        return False
    return _commit_is_grok_seat((row or {}).get("sha"), (row or {}).get("version"), repo=repo)


_AUTHOR_LOADED = {}


def _stamp_authors(repo):
    """ver -> author family, from the commits that set the stamp. -> dict

    One git log, not a show per version. The line that ADDS `"ver"` is the stamp.
    A later edit that leaves the version alone does not get to reassign the author.
    """
    out = {}
    try:
        log = subprocess.run(
            ["git", "log", "-n", "120", "--format=COMMIT %H%n%B%nENDMSG", "-p", "--",
             "tv/WINDOWS_SHIP.json"],
            cwd=repo, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=20)
        if log.returncode != 0:
            return out
    except Exception:
        return out
    # A stamp file is sometimes one JSON line (`{"ver": "v0002"}`) and sometimes a
    # pretty line (`  "ver": "v3577"`). Either way the added line is the ver this
    # commit wrote. A context line is a version this commit left alone.
    ver_rx = re.compile(r'^\+.*"ver"\s*:\s*"([^"]+)"', re.M)
    # REG-2011 (the #231 eye on v3577) - OLDEST FIRST. git log is newest-first and the first commit seen to add a
    # version kept it, so a later rewrite of the same "ver" line (a hand-fixed half-bump, a one-line stamp edited
    # for another field) took the authorship - and with it which family's look closes the version.
    for part in reversed((log.stdout or "").split("COMMIT ")[1:]):
        msg, _, diff = part.partition("\nENDMSG\n")
        added = ver_rx.findall(diff)
        if not added:
            continue
        ver = norm_version(added[-1])
        if not ver or ver in out:
            continue
        out[ver] = "xai" if _is_grok_seat_message(msg) else AUTHOR_FAMILY
    return out


def author_family(version, repo=None):
    """Who wrote this version, read from the commit that stamped it.

    A stamp whose message carries a `Seat: Grok CLI (code)` or `Seat: Grok Bot (code)` line is a Grok code
    seat, so its author family is xai. Every other stamp, and a version this cannot read,
    stays anthropic. The model string is not evidence: the recording tool strips a
    parenthesis, so a comment that merely says who wrote the ship decides nothing.
    """
    ver = norm_version(version)
    root = os.path.abspath(repo or _REPO)
    if not ver:
        return AUTHOR_FAMILY
    loaded = _AUTHOR_LOADED.get(root)
    if loaded is None:
        loaded = _stamp_authors(root)
        _AUTHOR_LOADED[root] = loaded
    return loaded.get(ver, AUTHOR_FAMILY)


def looked_at(version, path=None):
    """The rows that COUNT as a second-eye look at `version`, newest first.

    A row counts only when all three hold: the seat was reached, the family is a recognised one,
    and that family is not the one that wrote the code. Anything else is kept in the ledger and
    excluded here — recorded, but never mistaken for agreement.
    """
    v = norm_version(version)
    if not v:
        return []                          # a version we cannot name cannot be shown to be looked at
    out = []
    for r in _rows(path):
        if not isinstance(r, dict):
            continue                       # a line that parses but is not an object must not crash
        if norm_version(r.get("version")) != v:
            continue
        # ⚠ v2143.1 — RE-DERIVED, NOT TRUSTED. The first cut read the row's own `family` field, so
        # a hand-written line claiming family:"xai" satisfied the gate — the exact forgery this
        # ledger was introduced to make impossible, and I had told him it was. The stored field is
        # now evidence for a human reading the file; the DECISION is made from the model id alone.
        fam = family_of(r.get("model"))
        # The author is whoever stamped this version, not a module constant. A Claude
        # look on a Grok seat is the other family. A Grok look on that same seat is not.
        author = author_family(v)
        if fam is None and _claude_looked_at_a_grok_seat(r):
            # The line names both families, so family_of stays silent. The commit's seat
            # line says Grok wrote it, and Claude is then the other family.
            fam = "anthropic"
        if not fam or fam == author:
            continue
        # ⚠ strict True, not truthiness: the STRING "false" is truthy, and an adversarial pass used
        # exactly that to count an empty seat as a reached one.
        if r.get("reached") is not True:
            continue
        # v3403 — the eye was reached, cross-family and bound to evidence, and still said it could
        # not judge the change. That is not agreement; see _NOT_A_LOOK above.
        if row_is_not_a_look(r):
            continue
        # ⚠ a row must be bound to something. A hollow {version, model, reached} line proved a
        # look had happened while carrying no trace of one.
        #
        # v2145 — TWO CORRECTIONS FROM THE SECOND EYE, and the first is the serious one:
        #   · FINDINGS ARE EVIDENCE. record(..., findings=[...]) — the natural way to write down
        #     what the other family said — produced a row this refused, because only answerHead and
        #     images counted. So the honest path was: do the look, call the writer, and still be
        #     blocked. A gate that fails the correct behaviour trains the bypass.
        #   · images:[""] used to pass. An empty string in a list is not an image.
        if not _has_evidence(r):
            continue
        out.append(r)
    return sorted(out, key=lambda r: -(r.get("ts") or 0))


#: what a version stamp looks like in a diff line. ONE definition — `absent_kind` is its only
#: reader, and a second copy would disagree the day the stamp format changes. [[copy-drift]]
_VER_TOKEN_RX = re.compile(r"v\d{4}")

#: memo for absent_kind — a (sha, path) pair is finished history, so one answer is final.
_KIND_MEMO = {}

#: the repo root, so the git question is asked of THIS tree however the module was imported
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def absent_kind(sha, path):
    """Was this commit's change to `path` NOTHING BUT the version stamp? -> str.

        "stamp"        MEASURED: every changed line in that file carries a vNNNN token
        "substantive"  MEASURED: at least one changed line does not
        "unknown"      the diff could not be read (no sha, sha gone, path renamed)

    ⚠⚠ IT CLASSIFIES THE CHANGE, NEVER THE FILENAME, and that is the whole design. Across the
    last 120 version commits SIX files change in >=99% of them — tv/WINDOWS_SHIP.json, TASKS.md,
    tv/tv_diablo.py, bible.html, tv/control_app.py and BLUEPRINT.md — so a name allow-list looks
    obvious and is wrong in both directions. MEASURED, one filename, opposite verdicts:

        bible.html         @ e850b847 (v3345)  SUBSTANTIVE  37 changed lines — the apostrophe fold
        bible.html         @ c08875ad (v3352)  STAMP         2 changed lines, both version tokens
        tv/control_app.py  @ d2b3f3cf (v3343)  SUBSTANTIVE   8 changed lines — the rider route
        tv/control_app.py  @ c08875ad (v3352)  STAMP         2 changed lines, both version tokens

    An allow-list would excuse the two SUBSTANTIVE rows: a genuinely blind look waved through on
    the day one of those files IS the subject. [[the-unjoined-end]] §6 — a check that cannot
    discriminate is a constant wearing a measurement.

    ⚠ UNKNOWN IS NEVER AN EXCUSE. This function only ever REMOVES a warning, and it may do that
    only where the change was MEASURED to be a stamp. A diff nobody could read is not evidence
    that nothing was missed, so it stays outside the excuse. [[unknown-stays-unknown]]
    """
    sha = str(sha or "").strip()
    path = str(path or "").strip()
    if not sha or not path:
        return "unknown"
    key = (sha, path)
    if key in _KIND_MEMO:
        return _KIND_MEMO[key]
    out = "unknown"
    try:
        p = subprocess.Popen(["git", "diff", "--unified=0", "%s~1" % sha, sha, "--", path],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=_REPO)
        raw, _err = p.communicate(timeout=30)
        d = (raw or b"").decode("utf-8", "replace")
        body = [ln for ln in d.split("\n")
                if (ln.startswith("+") or ln.startswith("-"))
                and not ln.startswith("+++") and not ln.startswith("---")]
        if body:
            stampy = [ln for ln in body if _VER_TOKEN_RX.search(ln)]
            out = "stamp" if len(stampy) == len(body) else "substantive"
    except Exception:
        out = "unknown"
    _KIND_MEMO[key] = out
    return out


def _kinds_for(absent, given, sha):
    """The stored `absentKind`. Three states, exactly as `absent` has three.

    ⚠ CLASSIFIED AT THE DOOR so no caller can forget: `record()` takes the measurement itself
    unless one is handed in. [[heart-first]] §4 — instrument the single place things are created.
    """
    if absent is None:
        return None                       # nobody established reach at all
    if given is not None:
        return dict(given)                # the caller already measured it
    return dict((f, absent_kind(sha, f)) for f in absent)


#: v3464 — the #231 seat writes reach as ONE LINE of text: `path got/total, …, absent: a, b`
#: (or a `- path got/total` bullet list ending in `absent: none`). The local lane writes the
#: structured form `{path: {"got", "total"}}` directly. This is the ONE parser between the two.
_REACH_FILE = re.compile(r"(?<![\w./-])([\w.-][\w./-]*\.[A-Za-z0-9]+)\s+(\d+)\s*/\s*(\d+)(?![\w/])")
_REACH_ABSENT = re.compile(r"\babsent:\s*(.*)\Z", re.S | re.I)
_REACH_NONE = frozenset(("none", "nothing", "-", "n/a"))


def reach_from_line(line):
    """The seat's reach LINE -> (reach dict | None, absent list | None). ONE parser, two callers.

    ⚠⚠ v3464 — THE DRAIN STORED THE LINE AND agreement() COULD NOT READ IT. Found by the
    cross-family eye on the SHIPPED v3457 bytes (four findings on this path), then MEASURED over
    the 41 drained rows: 399 per-file sizes sat inside a string, so the cut walk below — which
    needs `{path: {"got", "total"}}` — skipped every one, and v3449's look, which held 810 of
    23,523 bytes (3.4%) of the file it reviewed, was filed as full agreement.

    The reach dict is the SAME SHAPE second_eye_run.reach_of() writes, plus the original `line`
    kept verbatim. `absent`: a list when the seat SAID (`absent: none` is a measured []), None
    when the line never mentions it — nobody said, which is not the same as nothing missing.
    ⚠ Everything after `absent:` is absent. The first cut split the whole line on commas and
    filed every file after the first as READ. [[unknown-stays-unknown]] [[copy-drift]]
    """
    if not line:
        return None, None
    s = str(line)
    reach = {"line": s}
    m = _REACH_ABSENT.search(s)
    for fm in _REACH_FILE.finditer(s[:m.start()] if m else s):
        reach[fm.group(1)] = {"got": int(fm.group(2)), "total": int(fm.group(3))}
    absent = None
    if m:
        tail = m.group(1).strip().rstrip(".")
        absent = ([] if tail.lower() in _REACH_NONE
                  else [p.strip() for p in re.split(r"[,\n]", tail) if p.strip()])
    return reach, absent


def _absent_of(row):
    """A row's absent list: the stored field, else what its own reach LINE said. -> list | None"""
    ab = row.get("absent")
    if ab is not None:
        return ab
    rc = row.get("reach")
    if isinstance(rc, dict) and rc.get("line"):
        return reach_from_line(rc["line"])[1]
    return None


def blind_to(row):
    """The absent files this look genuinely missed -> list, or None when reach was never recorded.

    A VERSION STAMP IS NOT A BLIND SPOT. MEASURED 2026-09-19 over the 7 rows carrying `absent`:
    v3349's counter flagged 7 of 7, and 12 of their 16 absent-file entries were bible.html or
    tv/tv_diablo.py changed by exactly two lines, both carrying a version token. Only TWO rows had
    missed anything a reviewer could have held an opinion about. A warning that fires on every row
    carries no information. [[regression-guard]] [[zero-needs-a-denominator]]
    """
    ab = _absent_of(row)
    if ab is None:
        return None
    kinds = row.get("absentKind") or {}
    out = []
    for f in ab:
        k = kinds.get(f)
        if k is None:
            # ⚠ NOT a back-filled guess. (sha, path) -> git is the SAME measurement from the SAME
            # source the writer would have taken, taken later. Every row written from v3354 on
            # carries it, so this path covers only the 7 legacy rows and then nothing.
            k = absent_kind(row.get("sha"), f)
        if k != "stamp":
            out.append(f)
    return out


#: ⚠ THE WHOLE VOCABULARY, IN ONE PLACE. A reader that pattern-matches these strings and has
#: never heard of a new one is the unjoined end this repo keeps paying for, so the set is named
#: rather than left implicit in five return statements.
#: MEASURED 2026-09-23, before ECHO existed, by grepping every caller of agreement() in the tree:
#:   · console_doctor._check_the_second_eye_was_asked_twice — DISAGREE/SINGLE -> MISSING,
#:     AGREE -> OK, and EVERYTHING ELSE falls through to UNKNOWN. A new state is therefore
#:     absorbed as "unknown", never as a pass and never as a red.
#:   · agreement_census() below — counts DISAGREE, and now ECHO beside it.
#:   · tv/test_two_looks_are_two_rows.py, tv/test_a_partial_look_is_not_agreement.py and
#:     tv/test_a_stamp_is_not_a_blind_spot.py — they pin AGREE/DISAGREE/SINGLE/NONE for rows that
#:     carry no model at all, which is the UNKNOWN-family case and is deliberately left on its
#:     old state (see below).
#: ⚠ CORRECTED v3459: an earlier version of this note said "ECHO lands in the fall-through ON
#: PURPOSE". That is no longer true — console_doctor now carries an explicit
#: `if st == "ECHO": return (MISSING, ...)` branch, because UNKNOWN means nobody could ask and
#: ECHO is a MEASUREMENT. The note outlived the code it described, which is the one thing a
#: comment must never do. [[feedback-comments-vs-code]]
#: INCOMPARABLE (v3459) is mapped the same way and for the same reason: it is measured, and the
#: comparable second look it is still owed is MINE to take, exactly like SINGLE.
#: Two looks whose payloads differ by this much are not answering the same question. 2.0x is
#: deliberately conservative: the two real pairs that provoked this were 2.9x and 9.9x, so the
#: bar sits below both without reclassifying a merely-slightly-larger look. #168.
_PAYLOAD_SPLIT = 2.0

AGREEMENT_STATES = ("NONE", "SINGLE", "AGREE", "ECHO", "DISAGREE",
                    "INCOMPARABLE")


def agreement(version, path=None):
    """Did two looks at ONE payload agree, and were they two WITNESSES? -> dict.

    His #56 ruling: ask twice and KEEP BOTH.

    FIVE STATES, and the fourth is the one #182 added:

        NONE      no reached look carries a verdict.
        SINGLE    asked once. One look cannot show whether the eye is steady.
        AGREE     two or more looks, same verdict, and at least two DIFFERENT families named —
                  or the families are UNKNOWN, which is stated in `say` rather than assumed.
        ECHO      two or more looks, same verdict, and every one of them MEASURED to be the SAME
                  family. One witness asked twice. Not a failure, not corroboration.
        DISAGREE  two or more looks, different verdicts — a finding about the INSTRUMENT, and
                  sharper still when the family is the same on both sides.

    ⚠⚠ ECHO IS NOT A RED STATE AND MUST NOT BECOME ONE. Eighteen of the twenty-nine multi-look
    versions on his ledger are same-family; making them report DISAGREE or MISSING would turn a
    whole population red on one day, and a row that cries wolf gets silenced — which costs more
    than the defect. ECHO withdraws exactly one claim: that these looks corroborate each other.

    ⚠ family None/"" IS UNKNOWN. It is never read as "some other family" (which would manufacture
    corroboration) and never as "the same family" (which would manufacture an echo). It blocks the
    ECHO claim, keeps the verdict-driven state, and is COUNTED in `say`. [[unknown-stays-unknown]]

    ⚠⚠ THIS EXISTS BECAUSE I WAS NOT ACTUALLY KEEPING BOTH. All through the v3301-v3309 arc I
    reported "asked twice, both looks agree" — and the ledger contains no such pairs, because I
    pasted the second look INTO the first answer's text as a bracketed note. `record_answer` then
    wrote ONE row carrying both. A second opinion that lives inside the first opinion's prose is
    not data: nothing can compute agreement from it and no disagreement can ever reach the heart.
    That is heart-first rule 6 — persist what you knew, not a summary of it — committed inside the
    mechanism built to catch exactly that. [[the-unjoined-end]]

    ⚠ IT CARRIES ITS OWN DENOMINATOR, ALWAYS. Measured 2026-09-18: 42 of 767 versions were ever
    asked twice — 5.5%. Any rate computed from this store is a rate over that 5.5%, and a
    percentage that does not say so is the confident number this repo keeps re-learning to
    distrust. [[zero-needs-a-denominator]]

    ⚠ AN EMPTY SEAT IS NOT AN OPINION. A row with reached=False is an unreachable eye, never
    agreement and never disagreement — it is excluded from both sides and counted separately, or
    two failed calls would read as a unanimous verdict. [[unknown-stays-unknown]]
    """
    version = norm_version(version)
    seen = [r for r in _rows(path) if norm_version(r.get("version") or "") == version]
    reached = [r for r in seen if r.get("reached") is not False]
    empty = len(seen) - len(reached)
    # ⚠ THE ROWS ARE KEPT, NOT ONLY THEIR VERDICTS. #182 has to ask WHO looked, and a list of
    # bare strings has already thrown that away by the time the decision is made.
    _spoke = [r for r in reached if str(r.get("verdict") or "").strip()]
    verdicts = [str(r.get("verdict") or "").strip() for r in _spoke]
    # ⚠⚠ #182 — THIS FUNCTION DECIDED AGREE/DISAGREE/SINGLE AND NEVER READ WHO LOOKED.
    # MEASURED 2026-09-23 over the live 941-row ledger: `family` is xai on 907 rows, openai on 22,
    # anthropic on 2 and UNKNOWN on 10. Of the 29 versions carrying two or more reached looks with
    # a verdict, EIGHTEEN are same-family (all xai), THREE are genuinely cross-family and EIGHT
    # cannot be told apart. Eight of those eighteen answered AGREE — and console_doctor maps AGREE
    # -> OK with no family filter, so "the looks agree" has been reported for one witness asked
    # twice. The carved rule, twice over: two derivations of one source agreeing is one number
    # wearing two names, and same-family agreement is ONE witness, not two.
    #
    # ⚠ RE-DERIVED FROM THE MODEL ID, NEVER FROM THE ROW'S OWN `family` FIELD. v2143.1 already
    # paid for that: a hand-written line claiming family:"xai" satisfied the gate built to stop it.
    # The stored field is evidence for a human reading the file; the DECISION comes from
    # family_of(), exactly as looked_at() does it.
    # ⚠ AND AN UNRECOGNISED id IS UNKNOWN, NEVER "some other family". It is counted apart, it
    # BLOCKS the ECHO claim (never assumed same) and it buys no corroboration either (never
    # assumed cross). [[unknown-stays-unknown]]
    _fams = [family_of(r.get("model")) for r in _spoke]
    _known = [f for f in _fams if f]
    _distinct = sorted(set(_known))
    _fam_unknown = len(_fams) - len(_known)
    #: MEASURED same-family: two or more looks, exactly ONE family named, and NOTHING
    #: unattributable. A single unknown id is enough to withdraw the claim.
    _same_family = (len(_spoke) >= 2 and len(_distinct) == 1 and _fam_unknown == 0)
    # ⚠⚠ v3349 — A LOOK THAT NEVER REACHED THE CHANGE IS NOT AN OPINION ABOUT IT. This is the
    # companion to the empty-seat rule above, and it is the quieter of the two: an empty seat is
    # visibly absent, while a PARTIAL look answers fluently about the fraction it was handed. On
    # v3347 the payload dropped 10 of 12 changed files including the one the version exists to
    # change, the eye said "all other listed files UNKNOWN", and the row was filed clean.
    # ⚠ THEY ARE NAMED, NOT EXCLUDED. What the eye said about the bytes it DID see is real
    # evidence and throwing it away would be its own lie; what must never happen is two partial
    # looks reading as AGREEMENT about a change neither of them saw.
    # ⚠ `absent` is UNKNOWN on every row written before this version (missing key or null), and
    # unknown is not zero — those rows are counted apart rather than assumed complete.
    # ⚠⚠ v3354 — A VERSION STAMP IS NOT A BLIND SPOT, and this counter was 71% noise. The line
    # replaced here read `[r for r in reached if r.get("absent")]`, firing on ANY absent file.
    # MEASURED 2026-09-19 over the 7 rows carrying `absent`: it flagged 7 of 7, while 12 of their
    # 16 absent-file entries were bible.html or tv/tv_diablo.py changed by exactly two lines, both
    # carrying a version token. Only TWO rows missed anything a reviewer could have held an
    # opinion about — v3349 (its own 218-line subject, filed `clean`) and v3351. A warning that
    # fires on every row is furniture, which is the same defect as a gate that is always green.
    # [[regression-guard]] [[zero-needs-a-denominator]]
    # ⚠⚠ v3363 — A FILE CAN ARRIVE AND STILL BE UNREAD, and the two counters above cannot see
    # it: both are answered by whether a `diff --git` header reached the payload. v3361's eye
    # OPENED with "REACH: 19/92 hunks" and the row read clean with blind_to [].
    _cutmap = {}
    for _r in reached:
        _rc = _r.get("reach")
        if not isinstance(_rc, dict):
            continue
        if _rc.get("line") and not any(isinstance(v, dict) for v in _rc.values()):
            # v3464 — a row drained before the parser existed carries only the seat's LINE.
            # Structure it with the same function the drain now uses at write time.
            _rc = reach_from_line(_rc["line"])[0] or _rc
        _n = sorted(p for p, v in _rc.items()
                    if isinstance(v, dict) and (v.get("total") or 0) > 0
                    and float(v.get("got") or 0) / float(v["total"]) < REACH_CUT_BAR)
        if _n:
            _cutmap[id(_r)] = _n
    _cut = [r for r in reached if id(r) in _cutmap]
    _blind = dict((id(r), blind_to(r)) for r in reached)
    _partial = [r for r in reached if _blind[id(r)]]
    _unknown_reach = [r for r in reached if _absent_of(r) is None]
    _pnote = ""
    if _cut:
        _cn = sorted(set(f for r in _cut for f in _cutmap[id(r)]))
        _pnote += (" ⚠ %d of %d look(s) got under %d%% of a file that DID arrive (%s)"
                   " — a header reaching the eye is not the file reaching the eye"
                   % (len(_cut), len(reached), int(REACH_CUT_BAR * 100),
                      ", ".join(_cn[:6])
                      + (" +%d more" % (len(_cn) - 6) if len(_cn) > 6 else "")))
    if _partial:
        _names = sorted(set(f for r in _partial for f in (_blind[id(r)] or [])))
        _pnote = (" ⚠ %d of %d look(s) NEVER SAW a SUBSTANTIVE part of the change (%s), so that "
                  "much of this is agreement about bytes nobody read"
                  % (len(_partial), len(reached),
                     ", ".join(_names[:6]) +
                     (" +%d more" % (len(_names) - 6) if len(_names) > 6 else "")))
        # v3897 (REG-3699) - and the row names the look that shows them: a follow-up at only those files
        # v3898 (the Grok CLI's look on v3897) - the COMMAND carries every name, each shell-quoted: it cut at six like the
        # prose and split a path with a space into two arguments, so the follow-up never asked for the set it named
        import shlex as _shlex
        _pnote += (" - `python3 tv/second_eye_run.py %s --files %s` shows them on their own"
                   % (version, " ".join(_shlex.quote(n) for n in _names)))
    # ⚠ THE DENOMINATOR TRAVELS WITH THE VERDICT: how many looks there were, and how many of
    # them the model id could attribute at all. A state that says AGREE while nobody knows who
    # looked is the confident number this file argues against on every other axis.
    # [[zero-needs-a-denominator]]
    _fnote = ""
    if _spoke:
        _fnote = (" · %d look(s), %d naming a family%s"
                  % (len(_spoke), len(_known),
                     (" (%s)" % ", ".join("%s %d" % (f, _known.count(f)) for f in _distinct))
                     if _distinct else ""))
        if _fam_unknown:
            _fnote += (" ⚠ %d of them name NO recognisable family, so whether this is one "
                       "witness or %d is UNKNOWN — not assumed cross-family, not assumed same"
                       % (_fam_unknown, len(_spoke)))
    if not verdicts:
        return {"version": version, "looks": 0, "empty": empty, "state": "NONE",
                "verdicts": [], "partial": len(_partial), "reachUnknown": len(_unknown_reach), "cut": len(_cut),
                "families": _distinct, "familyKnown": len(_known),
                "familyUnknown": _fam_unknown, "sameFamily": _same_family,
                "say": "no look with a verdict is recorded for %s%s" % (
                    version, (" (%d empty seat(s))" % empty) if empty else "") + _fnote + _pnote}
    if len(verdicts) == 1:
        return {"version": version, "looks": 1, "empty": empty, "state": "SINGLE",
                "verdicts": verdicts, "partial": len(_partial),
                "reachUnknown": len(_unknown_reach), "cut": len(_cut),
                "families": _distinct, "familyKnown": len(_known),
                "familyUnknown": _fam_unknown, "sameFamily": _same_family,
                "say": "%s was looked at ONCE (%s) — asked twice is his #56 ruling, and one look "
                       "cannot show whether the eye is steady on this payload"
                       % (version, verdicts[0]) + _fnote + _pnote}
    if len(set(verdicts)) == 1:
        # ⚠⚠ #182 — SAME FAMILY IS ONE WITNESS, AND IT GETS ITS OWN STATE RATHER THAN A RED
        # ONE. ECHO is deliberately NOT DISAGREE and NOT "no look": the eighteen same-family
        # versions on his ledger are real looks that really did agree, and reporting them as a
        # failure would turn a whole population red at once — a row that cries wolf gets silenced
        # inside a week, which costs more than the defect it was shouting about. The vocabulary
        # had room for a fifth word; SINGLE proves it. What ECHO refuses is the one claim that was
        # never earned: that these looks CORROBORATE each other.
        if _same_family:
            return {"version": version, "looks": len(verdicts), "empty": empty, "state": "ECHO",
                    "verdicts": verdicts, "partial": len(_partial),
                    "reachUnknown": len(_unknown_reach), "cut": len(_cut),
                    "families": _distinct, "familyKnown": len(_known),
                    "familyUnknown": _fam_unknown, "sameFamily": _same_family,
                    "say": ("%d looks at %s say the same thing (%s) and every one of them is %s "
                            "— that is ONE witness asked %d times, not corroboration. Two "
                            "derivations of one source agreeing is one number wearing two names."
                            % (len(verdicts), version, verdicts[0], _distinct[0], len(verdicts)))
                           + _fnote + _pnote}
        return {"version": version, "looks": len(verdicts), "empty": empty, "state": "AGREE",
                "verdicts": verdicts, "partial": len(_partial),
                "reachUnknown": len(_unknown_reach), "cut": len(_cut),
                "families": _distinct, "familyKnown": len(_known),
                "familyUnknown": _fam_unknown, "sameFamily": _same_family,
                "say": ("%d looks at %s AGREE (%s)" % (len(verdicts), version, verdicts[0]))
                       + _fnote + _pnote}
    # ⚠ A SAME-FAMILY DISAGREEMENT STAYS DISAGREE, and it is the sharper version of the same
    # finding: one family answering two ways about one payload is an unsteady INSTRUMENT, which is
    # exactly what this branch exists to say. ECHO is only ever reached when the verdicts match,
    # so nothing that used to read DISAGREE was moved out of it. MEASURED on his ledger: 10 of the
    # 29 multi-look versions are same-family disagreements and every one of them still reads
    # DISAGREE. `_fnote` now names the family, so the reader can tell the two shapes apart.
    # ⚠⚠ #168 (v3459) — "AT ONE PAYLOAD" WAS A CLAIM THIS FUNCTION NEVER CHECKED.
    # MEASURED on two real pairs it called unsteady:
    #     v3413   8,622 chars (cannot-tell)  vs  25,074 chars (findings)   — 2.9x
    #     v3451   7,744 chars (clean)        vs  76,810 chars (findings)   — 9.9x
    # An eye shown a tenth of the change answering differently from one shown all of it is not an
    # unsteady instrument; it is the CAP doing what the cap does. Blaming the eye points the reader
    # at the wrong subject and is precisely the conclusion that stops anyone looking at the cap.
    # ⚠ THE DATA WAS ALREADY IN THE ROWS AND THIS FUNCTION NEVER READ IT: `sentCode` and `chars`
    # appear NOWHERE in its body (checked by AST over every string constant, not by eye).
    # [[feedback-suspect-the-instrument]] [[label-outlived-referent]]
    _sizes = []
    for _r in reached:
        _sc = _r.get("sentCode")
        _n = (_sc or {}).get("chars") if isinstance(_sc, dict) else None
        if isinstance(_n, (int, float)) and _n > 0:
            _sizes.append(float(_n))
    _ratio = (max(_sizes) / min(_sizes)) if len(_sizes) >= 2 else None
    # ⚠⚠ v3461 — max/min OVER EVERY LOOK LETS ONE SMALL LOOK HIDE A REAL DISAGREEMENT.
    # Caught by the cross-family eye on the v3459 diff BEFORE it shipped, and then MEASURED on
    # v3401, which has THREE reached looks:
    #       8,885 chars  cannot-tell
    #      33,447 chars  cannot-tell
    #      33,447 chars  clean        <- IDENTICAL payload, DIFFERENT verdict
    # Two looks at exactly the same 33,447 chars disagree — a genuine unsteady eye, the sharpest
    # finding this function produces. But max/min across all three is 3.8x, so v3459 called the
    # whole version INCOMPARABLE and the real finding disappeared. A fix that swallows the defect
    # it was written beside is [[the-cure-that-kills-the-patient]].
    # SO THE QUESTION IS PER-PAIR, NOT PER-VERSION: if ANY pair that DISAGREES is also comparable,
    # that disagreement is real and the version stays DISAGREE. INCOMPARABLE is reserved for the
    # case where every disagreeing pair is a payload split.
    _real_split = False
    if _ratio is not None:
        _pairs = [(r, ((r.get("sentCode") or {}).get("chars")
                       if isinstance(r.get("sentCode"), dict) else None))
                  for r in reached]
        _pairs = [(r, n) for r, n in _pairs if isinstance(n, (int, float)) and n > 0]
        _comparable_disagreement = False
        for _i in range(len(_pairs)):
            for _j in range(_i + 1, len(_pairs)):
                _ra, _na = _pairs[_i]
                _rb, _nb = _pairs[_j]
                if str(_ra.get("verdict") or "") == str(_rb.get("verdict") or ""):
                    continue                      # they agree; not the pair in question
                if (max(_na, _nb) / min(_na, _nb)) < _PAYLOAD_SPLIT:
                    _comparable_disagreement = True
                    break
            if _comparable_disagreement:
                break
        _real_split = not _comparable_disagreement
    if _ratio is not None and _ratio >= _PAYLOAD_SPLIT and _real_split:
        return {"version": version, "looks": len(verdicts), "empty": empty,
                "state": "INCOMPARABLE",
                "verdicts": verdicts, "partial": len(_partial),
                "reachUnknown": len(_unknown_reach), "cut": len(_cut),
                "families": _distinct, "familyKnown": len(_known),
                "familyUnknown": _fam_unknown, "sameFamily": _same_family,
                "payloadRatio": round(_ratio, 1),
                "say": ("%d looks at %s reached DIFFERENT VERDICTS (%s) over payloads that differ "
                        "%.1fx (%d vs %d chars). That is NOT an unsteady eye — it is a different "
                        "question asked twice, and the comparable second look is still owed."
                        % (len(verdicts), version, ", ".join(verdicts), _ratio,
                           int(max(_sizes)), int(min(_sizes)))) + _fnote + _pnote}
    # ⚠ AND WHEN THE SIZES ARE UNKNOWN, THE "ONE PAYLOAD" CLAIM IS STILL UNEARNED. It is not
    # INCOMPARABLE either — nobody measured. The verdict stays DISAGREE and the sentence stops
    # asserting what was never checked. [[unknown-stays-unknown]]
    _one = ("at ONE payload" if _ratio is not None
            else "at payloads of UNKNOWN size (no sentCode.chars on %d of %d look(s))"
                 % (len(reached) - len(_sizes), len(reached)))
    return {"version": version, "looks": len(verdicts), "empty": empty, "state": "DISAGREE",
            "verdicts": verdicts, "partial": len(_partial),
            "reachUnknown": len(_unknown_reach), "cut": len(_cut),
            "families": _distinct, "familyKnown": len(_known),
            "familyUnknown": _fam_unknown, "sameFamily": _same_family,
            "payloadRatio": (round(_ratio, 1) if _ratio is not None else None),
            "say": "%d looks %s DISAGREE (%s) — the eye is not steady here, and which "
                   "verdict shipped was decided by timing. That is a finding about the "
                   "INSTRUMENT." % (len(verdicts), _one, ", ".join(verdicts)) + _fnote + _pnote}


#: ⚠⚠ v3315 — WHICH PARSER WROTE THIS VERDICT. Bump this string whenever `_verdict_for` or
#: `_findings_from` changes behaviour. Without it a row's verdict has no provenance, and a reader
#: cannot tell one written by today's parser from one written by a parser since corrected.
#:
#: MEASURED 2026-09-18 over all 824 rows: 64 carry `verdict="findings"` while their OWN STORED
#: ANSWER declares no defects were found — "No defects found in any of the four images.", and
#: several structured answers whose every slot reads "NOTHING FOUND". Re-judged with today's
#: parser, ALL 64 come back CLEAN, and 0 of them sat on the 600-char answerHead cap, so every one
#: of those re-judgements read the full stored text rather than a prefix.
#:
#: ⚠ SO THE PARSER IS NOT THE LIVE DEFECT — THE STORED ROWS ARE. v2808 and v3198 fixed the
#: parsing; nothing went back and said so, and nothing records which generation judged a row. Any
#: statistic over the ledger's history therefore reads 64 clean looks as looks that found
#: something. [[stale-reading]] — a verdict with no provenance is not a verdict.
#: v3363 — THE READER'S BAR for calling an ARRIVED file cut short. ⚠ It lives HERE and never in
#: the row: the row keeps got/total, so this number can move without rewriting history. A bar
#: baked into the store is the shape of the $5 he corrected me on and of the 0.22 threshold that
#: sat above a signal maxing at 0.133 — a branch that never ran.
#: MEASURED 2026-09-19 over 16 versions / 67 ARRIVED files: at 0.50 it names 8, including
#: tv/second_eye_ledger.py on v3354 at 48.6% — the file that version exists to change.
REACH_CUT_BAR = 0.50

PARSER_GEN = "v3376"

#: The verdicts `_verdict_for` can actually return. Anything else in the field was written by a
#: person and is not a parser judgement, so it must never be re-judged as though it were.
PARSER_VERDICTS = frozenset(("clean", "findings", "cannot-tell", ""))

#: The cap `record()` applies to a stored answer. A row sitting exactly on it is a PREFIX, and a
#: re-judgement of a prefix is not a judgement of the answer.
def answer_for_rejudge(row):
    """The text a re-judge may read, and whether it is the WHOLE answer. -> (text|None, complete)

    v3386 (#129) — THE ONLY HONEST WAY TO ASK "can this row be re-judged".

    Three outcomes, and the middle one is the point:
      (text, True)   the whole answer is stored; a parser change can be validated against it
      (text, False)  text is stored but was itself cut — usable, and it must NOT be called whole
      (None, False)  nothing beyond a prefix was ever kept. UNKNOWN, never "the head was all"

    ⚠ EVERY ROW WRITTEN BEFORE v3386 FALLS IN THE THIRD CASE, and that is 898 of them. Returning
    `answerHead` here instead would hand a re-judge a 400-character prefix and let it report a
    verdict as though it had read the answer — the confident-zero this whole file argues against.
    [[unknown-stays-unknown]] [[heart-first]] section 6
    """
    if not isinstance(row, dict):
        return None, False
    full = row.get("answerFull")
    if not isinstance(full, str) or not full:
        return None, False
    chars = row.get("answerChars")
    # complete only when the TRUE length agrees with what is stored; a missing answerChars is
    # UNKNOWN, so it reads as not-complete rather than as complete
    return full, bool(isinstance(chars, int) and chars == len(full))


ANSWER_HEAD_CAP = 600
#: v3386 — the ceiling on the FULL stored answer. Generous on purpose: the store is gitignored
#: and local (2.7 MB over 898 rows today), so the cost of keeping the evidence is a few MB and
#: the cost of losing it was every re-judge, for ever. It is a ceiling rather than "no limit" so
#: a runaway answer cannot fill his disk — and `answerChars` records the true length, so a row
#: that DID hit this ceiling says so instead of looking complete.
FULL_ANSWER_CAP = 200000


def verdict_provenance(path=None):
    """Which stored verdicts can still be trusted to mean what today's parser means. -> dict

    THIS NEVER WRITES. A stored verdict is the record of what was concluded at the time, and
    overwriting it would destroy the only evidence that the conclusion was ever different. What
    this does is MEASURE the disagreement so a reader can discount it.

    FOUR BUCKETS, and collapsing any of them into "agrees" is the defect:

        agree       today's parser reaches the same verdict on the stored answer
        disagree    it does not — the stored verdict is from a superseded generation
        prefixOnly  the stored answer sits on ANSWER_HEAD_CAP, so only a prefix survives and no
                    honest re-judgement is possible. UNKNOWN, never counted as agreement.
        noAnswer    nothing of the answer was stored at all. UNKNOWN for a different reason, and
                    kept apart because one is truncation and the other is absence.
    """
    out = {"total": 0, "stamped": 0, "unstamped": 0, "agree": 0, "disagree": 0,
           "prefixOnly": 0, "noAnswer": 0, "handWritten": 0, "which": [], "ok": True, "why": ""}
    try:
        # Lazy, and inside the function ON PURPOSE: second_eye_run imports THIS module, so a
        # top-level import here is a cycle. An unimportable runner is UNKNOWN, not clean.
        import second_eye_run as _run
    except Exception as exc:
        out["ok"] = False
        out["why"] = ("the verdict parser could not be imported (%s), so whether the stored "
                      "verdicts still mean what they say is UNKNOWN — not agreed"
                      % type(exc).__name__)
        return out

    for r in _rows(path):
        out["total"] += 1
        if r.get("judgedBy"):
            out["stamped"] += 1
        else:
            out["unstamped"] += 1
        # ⚠⚠ ONLY RE-JUDGE WHAT THE PARSER COULD HAVE WRITTEN. The verdict field also carries
        # HAND-WRITTEN annotations — "CORRECTION-to-my-own-earlier-row",
        # "CI-FOUND-TWO-THAT-THE-LOCAL-SUITE-COULD-NOT", "clean-for-the-shipped-change" — which
        # no parser ever produced. Comparing those against a parser verdict is a comparison
        # between two populations, and on the first run it manufactured 169 "disagreements" out of
        # annotations nobody ever claimed were parser output. That is precisely the defect v3313
        # removed from the seed row, reappearing one file away. [[unknown-stays-unknown]]
        if str(r.get("verdict") or "") not in PARSER_VERDICTS:
            out["handWritten"] += 1
            continue
        head = str(r.get("answerHead") or "")
        if not head.strip():
            out["noAnswer"] += 1
            continue
        # ⚠⚠ v3339 (#77) — ASK THE ROW WHAT IT WAS CUT TO. This tested a hardcoded 600 while the
        # RUNNER had already cut at 400, so 381 of 843 rows were re-judged as if the whole answer
        # were present and prefixOnly reported 98 where the honest figure is 479. The cap now
        # travels ON THE ROW.
        # ⚠ A LEGACY ROW HAS NO headCap AND THAT IS UNKNOWN, NOT WHOLE: rows written before this
        # sat on either the runner's 400 or the writer's 600, and nothing on disk says which. Both
        # are treated as prefix-only, which moves them OUT of agreement and never into it.
        _cap = r.get("headCap")
        if _cap is None:
            _prefix = len(head) in (200, 400, ANSWER_HEAD_CAP)
        else:
            _prefix = len(head) >= int(_cap)
        if _prefix:
            out["prefixOnly"] += 1
            continue
        try:
            # ⚠ `_verdict_for` returns a TUPLE (verdict, findings). Assigning it whole and
            # comparing against a verdict STRING can never match, so every row reads as a
            # disagreement — 709 of them on the first run, which is what a broken
            # instrument looks like when it is confident. Unpack it.
            now, _kept = _run._verdict_for(head, _run._findings_from(head))
        except Exception:
            out["noAnswer"] += 1
            continue
        if str(r.get("verdict") or "") == str(now):
            out["agree"] += 1
        else:
            out["disagree"] += 1
            if len(out["which"]) < 12:
                out["which"].append({"version": r.get("version"), "was": r.get("verdict"),
                                     "now": now, "head": head[:90]})

    _judged = out["agree"] + out["disagree"]
    out["say"] = ("%d of %d stored verdict(s) could be re-judged; %d still agree with today's "
                  "parser and %d DO NOT. %d could not be re-judged (%d stored only a prefix, %d "
                  "stored no answer, %d carry a HAND-WRITTEN verdict no parser produced) and are "
                  "UNKNOWN rather than agreeing. %d row(s) carry no parser stamp at all, so their "
                  "provenance is UNKNOWN by construction."
                  % (_judged, out["total"], out["agree"], out["disagree"],
                     out["prefixOnly"] + out["noAnswer"] + out["handWritten"],
                     out["prefixOnly"], out["noAnswer"], out["handWritten"],
                     out["unstamped"]))
    return out


def agreement_census(path=None, recent=40):
    """How much of the ledger can even answer the question. -> dict. ⚠ Denominator first.

    REG-2453 - kept per (ledger state, recent): a ledger that did not move is not walked again (a copy is handed back),
    and a census over readers a caller swapped in is never kept or served."""
    p = os.path.abspath(path or LEDGER_PATH)
    own = (_rows is _CENSUS_READERS[0] and agreement is _CENSUS_READERS[1]
           and verdict_provenance is _CENSUS_READERS[2])
    st = _ledger_state(p) if own else None
    key = (p, int(recent))
    if st is not None:
        hit = _CENSUS.get(key)
        if hit is not None and hit[0] == st["sig"]:
            return copy.deepcopy(hit[1])
    out = _census_walk(path, recent)
    if st is not None and _settled(st["sig"]) and _sig(p) == st["sig"] and _PARSED.get(p) is st:
        _CENSUS[key] = (st["sig"], copy.deepcopy(out))
    return out


def _census_walk(path=None, recent=40):
    """agreement_census's walk - every version, then one agreement() per recent asked-twice version."""
    seen = {}
    for r in _rows(path):
        v = norm_version(r.get("version") or "")
        if not v:
            continue
        seen.setdefault(v, []).append(r)
    asked_twice = [v for v, rs in seen.items()
                   if len([x for x in rs if x.get("reached") is not False
                           and str(x.get("verdict") or "").strip()]) >= 2]
    recent_v = sorted(asked_twice, key=_vnum)[-int(recent):]
    # ⚠ ONE agreement() CALL PER VERSION, NOT ONE PER QUESTION. It re-reads the whole ledger on
    # every call, so asking it twice would double a walk over 941 rows to answer two halves of one
    # measurement.
    _states = dict((v, agreement(v, path)["state"]) for v in recent_v)
    dis = [v for v in recent_v if _states[v] == "DISAGREE"]
    # #182 — AND HOW MANY OF THE PAIRS ARE ONE EYE ASKED TWICE. Kept apart from `disagreed`
    # because they are different findings with different remedies: one is an unsteady instrument,
    # the other is a corroboration that was never actually taken. Folding them together would hide
    # both. [[zero-needs-a-denominator]]
    echoed = [v for v in recent_v if _states[v] == "ECHO"]
    # ⚠⚠ v3461 — THE CENSUS DROPPED THE STATE v3459 HAD JUST ADDED, AND THAT MADE THE EYE LOOK
    # STEADIER. Found by the cross-family eye on the v3459 diff BEFORE it shipped, in one sentence:
    # "the new state is only half-joined". MEASURED on the live ledger the same minute:
    #     census said   disagreed=9  echoed=20
    #     actually      DISAGREE 9 · ECHO 20 · AGREE 4 · INCOMPARABLE 7
    # Seven versions counted by NOTHING. A reader watching `disagreed` fall from 19 to 12 reads it
    # as the instrument settling down, when those seven were RECLASSIFIED, not resolved — a number
    # improving because its denominator quietly lost rows.
    # ⚠ AND THIS FILE'S OWN VOCABULARY NOTE WARNS ABOUT EXACTLY THIS, a few hundred lines up:
    # "a reader that pattern-matches these strings and has never heard of a new one is the
    # unjoined end this repo keeps paying for". It was read, and the census was still missed.
    # [[the-unjoined-end]] [[zero-needs-a-denominator]]
    incomparable = [v for v in recent_v if _states[v] == "INCOMPARABLE"]
    # v3315 — the provenance rides WITH the rate. A disagreement rate computed over rows whose
    # verdicts were written by three different generations of the parser is a measurement of the
    # parser's history as much as of the eye's steadiness, and saying so is cheaper than the
    # reader discovering it. [[stale-reading]]
    _prov = verdict_provenance(path)
    return {"versions": len(seen), "askedTwice": len(asked_twice),
            "recent": len(recent_v), "disagreed": len(dis), "which": sorted(dis, key=_vnum),
            "echoed": len(echoed), "whichEchoed": sorted(echoed, key=_vnum),
            "incomparable": len(incomparable),
            "whichIncomparable": sorted(incomparable, key=_vnum),
            "provenance": _prov,
            # ⚠⚠ THE RATE IS AN UPPER BOUND, CONTAMINATED BY MY OWN WORKFLOW, AND MUST SAY SO.
            # A second ROW is not always a second OPINION. Measured 2026-09-18: v3300's two rows
            # are a wrapper misparse followed by the re-filed raw answer, and several older pairs
            # are corrections recorded against the same version. Those read as DISAGREE and are
            # not evidence of an unsteady eye. Presenting this figure as "the eye disagrees with
            # itself N% of the time" would be a confident number built from a 2.7% sample that
            # also contains artifacts — exactly the shape this repo keeps learning to distrust.
            # The honest use is the PER-VERSION verdict; this census exists to state the reach.
            # [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
            "say": ("%d of %d version(s) were ever asked twice (%.1f%%); of the %d most recent of "
                    "those, %d differed and %d were SAME-FAMILY (ECHO) — one witness asked "
                    "twice, which is not corroboration. ⚠ UPPER BOUND: a second ROW is not "
                    "always a second OPINION — re-files and corrections against one version "
                    "read as DISAGREE here, so this is not a measurement of the eye's steadiness. "
                    "%s"
                    % (len(asked_twice), len(seen),
                       100.0 * len(asked_twice) / max(1, len(seen)), len(recent_v), len(dis),
                       len(echoed),
                       _prov.get("say") or _prov.get("why") or ""))}


#: REG-2453 - the readers a kept census was built from; a census is kept or served only while these are still the module's
_CENSUS_READERS = (_rows, agreement, verdict_provenance)


def looked_at_commit(sha, path=None):
    """Has any different-family eye read THIS commit? -> True | False | None

    ⚠ None is a THIRD state and the important one: rows written before v3316 carry no sha, so a
    commit they reviewed is UNKNOWN here, never False. Returning False would make every look
    taken before this field existed read as "never looked at", which would demand the whole
    824-row history be bought again. [[unknown-stays-unknown]]
    """
    want = str(sha or "").strip()
    if not want:
        return None
    any_stamped = False
    for r in _rows(path):
        got = str(r.get("sha") or "").strip()
        if not got:
            continue
        any_stamped = True
        if r.get("reached") is False or not str(r.get("verdict") or "").strip():
            continue
        # accept either side being the abbreviated form; git shortens to 8 here
        if got.startswith(want) or want.startswith(got):
            return True
    return False if any_stamped else None


def largest_finished_look(path=None):
    """The biggest payload the eye has ever ANSWERED, in characters. -> int | None

    ⚠ None is a THIRD STATE and the important one: an empty ledger has witnessed nothing, so it
    cannot vouch for any cap. Returning 0 would make every cap look unwitnessed, and returning a
    large number would make every cap look fine — both are answers nobody measured.
    [[unknown-stays-unknown]]

    Only a row that was REACHED and came back with a verdict counts. An empty seat proves the
    payload was SENT, never that the eye could chew it, which is the whole question here.
    """
    best = None
    for r in _rows(path):
        if not isinstance(r, dict):
            continue
        if r.get("reached") is not True:
            continue
        if not str(r.get("verdict") or "").strip():
            continue
        sc = r.get("sentCode")
        n = sc.get("chars") if isinstance(sc, dict) else None
        if isinstance(n, int) and not isinstance(n, bool):
            if best is None or n > best:
                best = n
    return best


def cap_is_witnessed(cap, path=None):
    """Has the eye ever FINISHED a look at least this large? -> True | False | None

    v3418 — THE LAW BEHIND THE CAP, after Konyo raised it 9,000 -> 26,000 on 2026-09-22.

    A cap is a threshold, and this repo has paid twice for thresholds nobody measured against the
    thing they bound: `feedback-threshold-above-the-ceiling`. The old 9,000 was justified by
    "24,000 timed out at 240s" — true, and measured against a bound (EYE_TIMEOUT_S) that was later
    raised to 1200, so the evidence had quietly expired while the number stayed.

    So the rule is neither "9,000 is safe" nor "bigger is better": **a cap may only be a size the
    eye has actually been SEEN to finish at.** That can be checked, because every row records what
    was really sent. It refuses a blind raise, and it equally refuses a quiet lowering to a size
    the evidence does not support.
    """
    big = largest_finished_look(path)
    if big is None:
        return None
    try:
        return big >= int(cap)
    except Exception:
        return None


def owes_a_look(version, path=None):
    """True when `version` shipped and no different family has looked at it."""
    return not looked_at(version, path)


def _vnum(v):
    """vNNNN -> int, so versions order by NUMBER and not by the accident of their digit count."""
    try:
        return int(str(v or "").lstrip("vV") or -1)
    except Exception:
        return -1


def _shipped_versions(path=None):
    """Every version the ship table has ever recorded. -> (set, readable)

    ⚠ PARSED FROM TASKS.md, WHICH bump_version.py IS THE ONLY WRITER OF — never a second list
    here that would drift from it the first time a version is recorded by hand. [[copy-drift]]
    """
    import re as _re
    p = path or os.path.join(os.path.dirname(HERE), "TASKS.md")
    try:
        with io.open(p, encoding="utf-8") as fh:
            src = fh.read()
    except Exception:
        # ⚠⚠ "seed nothing, hide nothing" WAS WRONG, AND IT IS THE THIRD TIME IN THIS FAMILY.
        # Seeding nothing DOES hide: audit then emits no row for a shipped version that has no
        # ledger data, while --check still blocks it — the exact contradiction this seeding
        # exists to end, reachable by a permission error or a bad tasks_path. The caller is told
        # so it can SAY so. [[zero-needs-a-denominator]]
        return set(), False
    # ⚠ NO UPPER BOUND ON THE DIGITS. `v\d{3,5}` gave the parser an expiry at v100000 while its
    # own contract says "every version the ship table has ever recorded" — a six-digit release
    # would be silently ignored and get no OWED row.
    return set(_re.findall(r"^\|\s*\*\*(v\d{3,})\*\*\s*\|", src, _re.M)), True


def audit(path=None, tasks_path=None, state=None):
    """Every version mentioned in the ledger, and whether it was really seen.

    ⚠ v2145 — THIS USED THE RULES `looked_at` HAD ALREADY ABANDONED, and the second eye measured
    both directions of the resulting contradiction: a forged row (model:"", family:"xai") that
    --check REFUSED was listed here as "OK looks=1", and a real look recorded as version "9999"
    that --check ACCEPTED was listed here as OWED. The test named
    test_check_and_audit_cannot_disagree_about_a_bare_number never called audit(), so the
    disagreement it claimed to close was still there, both ways.

    audit() is also the recovery command the refusal message tells him to run, which makes a
    contradiction here worse than one anywhere else: it is the screen he reads when he is already
    blocked. One rule, asked from both. [[feedback-contradiction-is-the-finding]]
    """
    seen = {}
    # ⚠⚠ A VERSION WITH NO ROW AT ALL WAS INVISIBLE HERE, AND THOSE ARE THE ONES THAT BLOCK. This
    # walked the ledger only, so a version nobody ever recorded anything for simply did not appear
    # — while `--check` refuses it by name. MEASURED: --audit listed 5 OWED and NOT v3156, whose
    # own --check says "nothing was ever recorded for it". audit() is the command the refusal
    # message tells him to run, so the screen he reads when he is already blocked was the one
    # screen that could not show the block. [[zero-needs-a-denominator]] [[the-unjoined-end]]
    #
    # ⚠ BOUNDED TO THE ERA THE LEDGER COVERS. TASKS.md carries every version ever shipped; seeding
    # all of them would bury today's two OWED rows under hundreds of versions that predate the eye
    # lane and were never expected to carry a look. Anything at or after the OLDEST version the
    # ledger knows about was expected to; anything before it was not.
    # ⚠ ONE SNAPSHOT, NOT TWO PASSES. The floor was computed from one _rows() walk and the rows
    # built from a second; a rolling prune or a rotation between them lets the cutoff describe the
    # old ledger while the listing describes the new one. This file is JSONL and IS pruned.
    _snapshot = list(_rows(path))
    _ledger_versions = set()
    for r in _snapshot:
        v = norm_version(r.get("version"))
        if v:
            _ledger_versions.add(v)
    # ⚠ NUMERICALLY, NOT AS STRINGS — 'v1000' >= 'v999' is FALSE, so a four-digit version would
    # have been dropped the moment the counter rolled past v999. Found by the Codex eye on v3157.
    _floor = min(_vnum(v) for v in _ledger_versions) if _ledger_versions else None
    # ⚠⚠ AND AN EMPTY LEDGER SEEDS EVERYTHING, WHICH IS THE WHOLE POINT OF THIS BLOCK. A `None`
    # floor used to seed NOTHING, so a ledger with no rows listed no versions at all — the exact
    # defect this seeding exists to kill, one level down: when nobody has ever looked at anything,
    # EVERY shipped version owes a look and the screen must say so. [[zero-needs-a-denominator]]
    _shipped, _ship_ok = _shipped_versions(tasks_path)
    # ⚠ HANDED BACK TO THIS CALLER, NOT LEFT IN A MODULE GLOBAL. v3160 stashed it in
    # LAST_SHIP_TABLE_OK, which two concurrent audits race over: audit A reads an unreadable table
    # and, before its caller prints, audit B reads a good one and flips the flag — so A omits the
    # warning and hides exactly the rowless versions this seeding exists to surface. The inverse
    # warns about a table that was fine. A per-call dict cannot be overwritten by anyone else.
    # Found by the Codex eye on v3160. [[the-unjoined-end]]
    if isinstance(state, dict):
        state["shipTableOk"] = _ship_ok
    for v in _shipped:
        if _floor is None or _vnum(v) >= _floor:
            seen.setdefault(v, {"version": v, "attempts": 0, "empty": 0, "author": 0,
                                "looks": 0, "cannot": 0, "bound": 0, "unbound": 0})
    for r in _snapshot:
        v = norm_version(r.get("version")) or (str(r.get("version") or "?").strip() or "?")
        st = seen.setdefault(v, {"version": v, "attempts": 0, "empty": 0, "author": 0,
                                 "looks": 0, "cannot": 0, "bound": 0, "unbound": 0})
        st["attempts"] += 1
        fam = family_of(r.get("model"))          # re-derived, exactly as the verdict does it
        if fam is None and _claude_looked_at_a_grok_seat(r):
            fam = "anthropic"
        author = author_family(v)
        if r.get("reached") is not True:
            st["empty"] += 1
        elif fam and fam == author:
            st["author"] += 1
        elif fam and _has_evidence(r) and row_is_not_a_look(r):
            # ⚠⚠ v3415 — A COULD-NOT-JUDGE IS NOT A LOOK, AND THIS SURFACE WAS THE LAST TO
            # LEARN IT. v3403 taught `looked_at` (and therefore the push gate) that
            # `cannot-tell` does not count; audit() kept counting it, so ONE row was read two
            # ways: MEASURED on v3413 — looked_at() 0, owes_a_look() True, audit() looks=1.
            # The gate refused the push while its own refusal message pointed at --audit, the
            # one screen calling that row fine. `looks` feeds THREE surfaces (the --audit mark,
            # the --audit headline, and --backlog's queue), so all three were blind together
            # and fixing them separately would have been three chances to drift again.
            # [[the-unjoined-end]] [[copy-drift]] [[feedback-contradiction-is-the-finding]]
            st["cannot"] += 1
        elif fam and _has_evidence(r):
            st["looks"] += 1
            # ⚠ v2708 — AND SAY WHETHER THE LOOK IS BOUND TO BYTES. `looks=1` was printed
            # identically for a look taken against this version's own file and for one inherited
            # from a batch — 16 looks carry 40 version rows between them. A count that cannot say
            # what it counted is the shape this repo keeps paying for, so the audit now reports
            # both numbers and never folds them. Rows written before this field existed are
            # UNBOUND, not wrong: nobody recorded it, and backfilling a plausible hash would forge
            # the very evidence the field exists to supply. [[unknown-stays-unknown]]
            if isinstance(r.get("bytes"), dict) and r["bytes"].get("bible"):
                st["bound"] += 1
            else:
                st["unbound"] += 1
        else:
            st["empty"] += 1                     # unidentifiable, or bound to nothing
    return sorted(seen.values(), key=lambda s: s["version"])


def _encoding_safe():
    """His suite caught this one on the first run: a CLI that prints non-ASCII and never makes
    stdout encoding-safe CRASHES WHILE REPORTING on a non-UTF-8 console, and a clean tree then
    exits non-zero for a reason that has nothing to do with the thing being checked. He runs a
    Windows machine, so that console is real. Same idiom as js_syntax_gate.py:439-443.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main(argv):
    _encoding_safe()
    argv = list(argv or [])

    # ⚠ v2143.1 — THE GATE MUST NOT BE REDIRECTABLE BY THE PUSHER'S ENVIRONMENT. LEDGER_PATH honours
    # TV_SECOND_EYE_LEDGER so tests can point it at a fixture, and an adversarial pass showed that a
    # one-word prefix on the push command therefore disarms the whole thing with no --no-verify and
    # no trace. `--gate` (which is what hooks/pre-push passes) pins the canonical path and ignores
    # the variable entirely. Tests keep the seam by calling the functions with an explicit `path=`.
    global LEDGER_PATH
    if "--gate" in argv:
        # #178 (REG-2450) - and the canonical path is THIS MACHINE's ledger (git's common dir), never the pushing tree's
        # own file: a fresh push worktree has none, and a look recorded in one died with it.
        LEDGER_PATH = _MACHINE_LEDGER
        if LEDGER_WHY is None:
            try:
                fold(LEDGER_PATH)
            except Exception as e:
                print("second eye: ⚠ the checkouts' own ledgers could not be folded in (%s) - the gate reads this "
                      "machine's ledger as it stands" % type(e).__name__)
    if LEDGER_WHY is not None and LEDGER_PATH == _MACHINE_LEDGER:
        print("second eye: ⚠ %s, so this tree keeps its OWN ledger (%s) - it dies with the tree"
              % (LEDGER_WHY, LEDGER_PATH))

    # ⚠ and --check must not be swallowed by --audit appearing anywhere in argv, which printed
    # "OWES A LOOK" and then exited 0 — a refusal that reads as a pass.
    if "--check" in argv:
        return _cmd_check(argv)
    if "--audit" in argv:
        _state = {}
        rows = audit(state=_state)
        if not rows:
            print("second eye: the ledger is empty — nothing has ever been looked at.")
            return 0
        # ⚠ THE HEADLINE EXISTS BECAUSE THE FULL TRUTH IS LONG. Seeding from the ship table took
        # this listing from 5 rows to 166 — every one of them real, and the two he can act on
        # buried among them. A screen he must scroll to find the block is barely better than one
        # that hid it. So: say the count, name the newest that owe, then print everything.
        if not _state.get("shipTableOk", True):
            print("second eye: \u26a0 the ship table could not be READ, so versions with no "
                  "ledger row cannot be listed here at all. This listing is the ledger only — "
                  "--check may still refuse a version this screen does not show.")
        _owed = [r for r in rows if not r["looks"]]
        _newest = [r["version"] for r in _owed][-6:]
        print("second eye: %d of %d version(s) in the ledger era carry NO look%s"
              % (len(_owed), len(rows),
                 (" — newest owing: " + ", ".join(reversed(_newest))) if _newest else ""))
        for s in rows:
            mark = "OK " if s["looks"] else "OWED"
            print("  %-6s %-8s looks=%d  empty-seats=%d  author-only=%d%s"
                  % (mark, s["version"], s["looks"], s["empty"], s["author"],
                     ("  cannot-tell=%d \u2014 recorded, and NOT a look"
                      % s["cannot"]) if s.get("cannot") else ""))
        return 0

    print(__doc__.strip().split("\n")[0])
    print("usage: second_eye_ledger.py --audit | --check [vNNNN] [--gate]")
    return 0


def _cmd_check(argv):
    if True:
        i = argv.index("--check")
        want = argv[i + 1] if len(argv) > i + 1 else current_version()
        # ⚠ the hook interpolates a value it read off disk straight into argv. An adversarial pass
        # set it to "--audit" and turned the check into a printed pass. Anything that is not a
        # version is UNKNOWN, and unknown exits non-zero.
        if want is not None and not norm_version(want):
            print("second eye: %r is not a version — refusing rather than guessing." % (want,))
            return 2
        if not want:
            print("second eye: cannot tell which version to check — no version given and "
                  "WINDOWS_SHIP.json did not yield one.")
            return 2                      # unknown is not a pass
        if owes_a_look(want):
            rows = [r for r in _rows() if r.get("version") == want]
            why = "nothing was ever recorded for it"
            if rows:
                author = author_family(want)
                empt = sum(1 for r in rows if not r.get("reached"))
                auth = 0
                for r in rows:
                    if not r.get("reached"):
                        continue
                    fam = family_of(r.get("model"))
                    if fam is None and _claude_looked_at_a_grok_seat(r):
                        fam = "anthropic"
                    if fam and fam == author:
                        auth += 1
                bits = []
                if empt:
                    bits.append("%d empty seat(s) — the eye was not reached" % empt)
                if auth:
                    bits.append("%d look(s) from the family that WROTE it, which is not a second eye"
                                % auth)
                cant = sum(1 for r in rows
                           if r.get("reached") and row_is_not_a_look(r))
                if cant:
                    bits.append("%d look(s) where the eye answered that it COULD NOT JUDGE the "
                                "change — widen the payload or re-ask; re-pushing changes nothing"
                                % cant)
                if bits:
                    why = "; ".join(bits)
            print("second eye: %s OWES A LOOK — %s" % (want, why))
            return 1
        r = looked_at(want)[0]
        # v2145 — PRINT WHAT THE VERDICT USED. This line read the STORED `family` field, which
        # looked_at had just refused to trust: a row {model:"grok-4", family:"anthropic"} counted
        # (re-derived xai) and then announced itself as "looked at by grok-4 (anthropic)". A
        # success message that contradicts the rule that produced it is how a reader learns to
        # stop believing the messages. [[label-outlived-referent]]
        # A Claude line that also names the Grok seat is ambiguous to family_of, and looked_at
        # counts it from the commit. Say that family, not None.
        _fam = family_of(r.get("model"))
        if _fam is None and _claude_looked_at_a_grok_seat(r):
            _fam = "anthropic"
        print("second eye: %s was looked at by %s (%s) — %s"
              % (want, r.get("model"), _fam,
                 r.get("verdict") or "no verdict recorded"))
        return 0



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
