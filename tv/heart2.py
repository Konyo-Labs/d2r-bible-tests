#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""♥♥ HEART 2.0 — the instruments watch themselves.

    python3 tv/heart2.py --report      the census: proven · blind · unproven · unprovable
    python3 tv/heart2.py --prove       re-tamper every guard that declares a proof, in a SANDBOX
    python3 tv/heart2.py --prove NAME  just this one
    python3 tv/heart2.py --prove NAMES --push
                                       what hooks/pre-push runs (#42): a proof that declares "widths" runs its clean
                                       AND tampered runs only at those viewports; the proofs likeliest to fail run
                                       first and the run STOPS at the first BLIND / INVALID / clean-run red; a gate
                                       that starts a browser is proved one at a time, whatever the lane count; and
                                       (P3) a PROVEN is reused from tv/.heart2_cache.json when every byte it depends
                                       on is identical - HEART2_PROVE_CACHE=0 runs everything
    python3 tv/heart2.py --detect      what no gate covers, dropping what is already covered
    python3 tv/heart2.py --ratchet     the unproven backlog may only ever shrink

═══════════════════════════════════════════════════════════════════════════════════════════════
THE DISTINCTION THAT MAKES IT v2
═══════════════════════════════════════════════════════════════════════════════════════════════

    heart v1   is the SYSTEM healthy?      — lanes, routes, stores, the console
    heart v2   are my own INSTRUMENTS      — the gates and the locks themselves
               still alive?

**MEASURED 2026-09-08, and this is the whole argument.** The heart was GREEN while 12 of 238 gates
were red, 8 of those were blind instruments, and the full set had been failing in CI since
2026-09-07 06:12 — 28 of the last 40 runs. Every check the heart made was working. Nothing was
checking the checkers, so nobody knew.

Three of the eight were laws that had silently STOPPED MEASURING what they claimed while staying
green — q-level probes written when set pieces had no data, still passing, grading nothing.

═══════════════════════════════════════════════════════════════════════════════════════════════
THE NUMBER THAT SETTLES "isn't it basically built?"
═══════════════════════════════════════════════════════════════════════════════════════════════

    gates registered                          247
    Wilson locks with a re-runnable harness     19
    gates with an EXECUTABLE red-proof           0      <- before this file
    test files even STATING a red-proof           1

Every one of those gates was proven red exactly once, by hand, in a shell, and that proof survives
only as prose in a docstring. It cannot be re-run. **So the number of gates that can still go red
is UNKNOWN — not zero, not fine. Unknown.** [[unknown-stays-unknown]]

═══════════════════════════════════════════════════════════════════════════════════════════════
THE PROTOCOL
═══════════════════════════════════════════════════════════════════════════════════════════════

A gate declares its own defeat, executably, beside itself:

    RED_PROOF = [{
        "why":     "what the law is FOR — the defect, in one line",
        "file":    "control_app.py",        # relative to tv/
        "find":    "<the exact bytes that make the law hold>",
        "replace": "<the bytes that reintroduce the defect>",
        "matches": 1,                       # EXACT count expected
    }]

and `--prove` does four things per proof, in this order, because each one catches a different lie:

  1. **CLEAN RUN in the sandbox.** The gate must PASS untampered. If it fails clean, the sandbox is
     wrong and nothing after it means anything — reported UNPROVABLE, never BLIND.
  2. **MATCH COUNT.** `find` must occur exactly `matches` times. A sabotage that matches 0 times
     changes nothing and the gate stays green for the most boring reason there is. Six times in one
     day the sabotage was the broken thing, not the law. **PRINT THE MATCH COUNT.**
     [[sabotage-is-usually-the-wrong-one]]
  3. **TAMPER AND RE-RUN.** The gate must now FAIL.
  4. **RESTORE**, so the next proof starts from clean bytes.

A gate that survives its own defeat is **BLIND** — the finding this whole file exists to produce.

⚠⚠ THE SANDBOX IS THE SAFETY STORY, AND IT IS NOT OPTIONAL. Achilles corrupted real journals by
tampering in place (its REG-011). Here the same mistake is worse: `tv/` holds 5.8 GB of his footage,
and a `cp -R` of it already caused an ENOSPC that broke every Bash call in a session — nobody could
run `df`, let alone `rm`. So: `safe_copy.py`, which excludes frames/.render_shots/.git/node_modules,
refuses above 400 MB and refuses any copy leaving under 4 GB free. Measured: tv/ is 5,865 MB, the
safe copy is 43.7 MB. **Never `cp -R`.**

⛔ IT PROPOSES INTO A FILE. IT NEVER EDITS A GUARD. Achilles' reason stands verbatim: *"In one night
working this tree I introduced three defects while fixing others, and I can read a diff."* A tool
that repairs its own instruments can talk itself into anything.

⚠ A RATCHET, NOT A BAN. 247 gates cannot grow proofs in one pass, and a law that fails on all of
them is one nobody can ship. Mandatory for every NEW gate; the backlog burns down.
"""
import argparse
import ast
import atexit
import contextlib
import hashlib
import io
import json
import os
import time
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass

# v3848 - TV_HEART2_STATE lets the render sandbox's private console read a SYNTHETIC census when this tree has none
# (a fresh worktree, CI). Unset everywhere else, so every prove and census still reads and writes the tree's own file.
STATE = os.environ.get("TV_HEART2_STATE") or os.path.join(HERE, ".heart2.json")
PROPOSALS = os.path.join(HERE, ".heart2_proposals.md")
#: REG-2355 — the rule a census's BLIND list was judged under. 2: a proof whose every case skipped FOR NODE in both runs,
#: on a PC with no node, is ELSEWHERE, never BLIND (REG-2354, REG-2359). A census filed under an older rule owes those
#: BLIND gates again, by name (blind_rule_owed), until each has been judged under this one; self_prove reads the census
#: stale till then.
BLIND_RULE = 2

PROVEN, BLIND, UNPROVEN, UNPROVABLE, INVALID = "PROVEN", "BLIND", "UNPROVEN", "UNPROVABLE", "INVALID"
#: REG-1686 — a red-proof whose tamper can only be judged on a PC that HAS something (`"needs": "<capability>"`) is
#: ELSEWHERE on a PC without it: measured where the thing is, never BLIND here. MEASURED 2026-10-01: his ALT (no local
#: D2R install - it plays through a cloud client) filed test_the_character_builder_is_their_builder BLIND on proofs [9]
#: and [10]; the one case that drives the generator skips in BOTH runs there ("UNMEASURED here, not passed"), so the
#: tampered run stayed green about nothing - and that one BLIND record shut every lock on the PC, the river with it.
ELSEWHERE = "ELSEWHERE"
#: capability -> (module, probe, his words for it). A name not listed here is INVALID: a typo must never excuse a proof.
PROOF_NEEDS_HOST = {
    "d2r-install": ("affix_lexicon", "install_present", "the D2R install (its CASC data and the extractor)"),
    # REG-2366 — a directory link in the temp dir: a symlink, or a junction on Windows (no privilege, REG-1668). The
    # scratch-listing law's realpath proof has one catcher, a link inside the scratch pointing at the tree; his ALT and
    # Dean's PC refuse the symlink, the case skipped in both runs and the proof read BLIND there. The probe makes a link
    # exactly as the law does (fixture_tmp.link_dir) and asks realpath to resolve it; a PC that can do neither reads
    # that proof ELSEWHERE.
    "dir-link": ("fixture_tmp", "can_link_a_directory",
                 "a directory link in its temp dir (a symlink, or a junction on Windows) that realpath resolves"),
    # REG-1688 — the ALT filed test_a_stub_agent_never_films_his_screen BLIND on [2] and [3]: the film loop it guards
    # starts only on macOS (start_film_thread returns unless sys.platform == "darwin"), and the law reaches the farewell
    # look with SIGTERM, which on Windows ends the process before any handler runs.
    "macos": ("heart2", "_host_is_macos", "macOS (the code it guards runs only there)"),
    "posix-signals": ("heart2", "_host_has_posix_signals",
                      "a SIGTERM that reaches the process's handler (Windows ends the process instead)"),
    # REG-1719 — the ALT on v3556 filed four gates BLIND; three judged code its Windows PC never runs. numpy: the ALT
    # has none, so the inventory lattice cannot read a frame there and every lattice law skips (all 7 cases, both
    # tamper and clean). posix: the prover's birth read runs `ps` through fork_exec only off Windows.
    "numpy": ("heart2", "_host_has_numpy", "numpy (the inventory lattice reads a frame only with it)"),
    "posix": ("heart2", "_host_is_posix", "a POSIX process table (ps through fork_exec; Windows reads births another way)"),
    # REG-2354 — MEASURED on Dean's PC 2026-10-21: no node and no bash on PATH (tv/install-tvd.ps1 installs neither), so
    # its census filed 56 gates BLIND - 53 JS laws whose every case skipped for want of node in both runs, 1 whose
    # catching laws skip for want of node, 1 for want of bash, 1 stale tamper - and one BLIND shuts every lock on a PC:
    # 0 of 9 permitted there, 135 reels on disk and not one ever tombstoned. Measured where the tool is, never BLIND here.
    "node": ("heart2", "_host_has_node", "Node.js on PATH (the law runs the page's own JavaScript through node)"),
    "bash": ("heart2", "_host_has_bash", "bash on PATH (the law runs a hook script through bash)"),
    # REG-2592 — MEASURED on the 16-shard CI run at dcff7160: five gates stranded their shard because each asks about
    # HIS venue, not about code, and a runner has none of it. Each probe asks the gate's OWN venue question (one truth,
    # never re-derived here), and lives in the gate's module: heart2 imports none of them (browser_gates reads heart2's
    # imports, and overlap_ratchet's closure reaches a browser - one import here put 699 gates under the lock, not 69).
    # live-panel and vault_wilson's live-witness door need a console on 17772; human-eyes needs
    # his ledger; reel_demo needs footage on the shelf; overlap_ratchet needs a baseline measured on this platform.
    "live-console": ("live_panel_gate", "console_here",
                     "a running console on 127.0.0.1:17772 (the law reads the LIVE page, which no sandbox tamper reaches)"),
    "human-eyes-ledger": ("human_eyes_ledger", "ledger_here",
                          "his human-eyes ledger (a gitignored runtime record that exists only where the loop runs)"),
    "reel-shelf": ("reel_demo", "shelf_here", "footage on his reel shelf (tv/frames is gitignored)"),
    "overlap-venue": ("overlap_ratchet", "venue_here",
                      "the platform the overlap baseline was measured on (font metrics differ across platforms)"),
}


def _host_is_macos():
    """REG-1688 — the PROOF_NEEDS_HOST probe for "macos". -> bool"""
    return sys.platform == "darwin"


def _host_has_posix_signals():
    """REG-1688 — the PROOF_NEEDS_HOST probe for "posix-signals". -> bool"""
    return not sys.platform.startswith("win")


def _host_has_numpy():
    """REG-1719 — the PROOF_NEEDS_HOST probe for "numpy". -> bool (asks the import system; imports nothing)"""
    import importlib.util as _ilu
    return _ilu.find_spec("numpy") is not None


def _host_is_posix():
    """REG-1719 — the PROOF_NEEDS_HOST probe for "posix". -> bool"""
    return os.name == "posix"


def _host_has_node():
    """REG-2354 — the PROOF_NEEDS_HOST probe for "node". -> bool (asks PATH the way the JS laws do; runs nothing)"""
    return shutil.which("node") is not None


def _host_has_bash():
    """REG-2354 — the PROOF_NEEDS_HOST probe for "bash". -> bool (the question the hooks law's skipUnless asks)"""
    return shutil.which("bash") is not None


def host_lacks(need):
    """REG-1686 — does THIS PC lack what a red-proof declared it needs? -> (True | False | None, words)

    True: the proof is ELSEWHERE here. False: judge it as usual. None: the name is not a declared capability (the proof
    is INVALID) or the probe itself failed - judged as usual then, so a broken probe can never soften a verdict."""
    spec = PROOF_NEEDS_HOST.get(str(need or ""))
    if spec is None:
        return None, "an undeclared capability %r" % (need,)
    mod, fn, words = spec
    try:
        import importlib
        return (not bool(getattr(importlib.import_module(mod), fn)())), words
    except Exception as e:
        # v3842 (v3841 second eye) - None, as the docstring says: False here let _cache_serve serve a carried PROVEN
        # over a probe that never answered. None is judged as usual by _prove_one and never served by _cache_serve.
        return None, "%s (its probe failed: %s - judged as usual)" % (words, type(e).__name__)


# ── finding the gates ────────────────────────────────────────────────────────────────────────
def _stale_say(v):
    """What the ratchet cannot see, in words a reader can act on. -> str

    ⚠ A NUMBER WITH NO SENTENCE IS A NUMBER NOBODY ACTS ON. `coverageStaleNodes: 30` means thirty
    watched nodes could disappear and every automated check would still read clean, and that is not
    obvious from the integer. UNKNOWN is said out loud rather than rendered as a quiet zero.
    """
    n = v.get("coverageStaleNodes")
    if not isinstance(n, int):
        return ("how much slack this ratchet carries is UNKNOWN — the render verdict predates the "
                "measurement, so nothing here says whether a watched node could vanish unseen")
    if not isinstance(v.get("coverageFloorKnown"), bool):
        return ("%d node(s) of slack were counted, but whether a floor exists at all is UNKNOWN, "
                "so this number has no denominator" % n)
    if not v.get("coverageFloorKnown"):
        return "there is no coverage floor yet, so the ratchet cannot fire for any target"
    if n <= 0:
        return "no slack: every floor sits at what a clean run actually photographs"
    return ("%d node(s) of slack — that many watched nodes could vanish and this ratchet would "
            "still read clean, because each floor sits below what a clean run photographs" % n)


def _fan_state(rec):
    """What one width's payload actually IS. -> 'reading' | 'threw' | 'unread'

    ⚠⚠ v2928 — THE WRITER HAS THREE STATES AND v2926's READER HAD TWO. Caught by the cross-family
    eye and reproduced: `control_ui.html` writes `{ok:false, threw:"..."}` when `_hrtFanFit` raises,
    and `{ok:false, reverted:false, ...}` for its own `no fan` / `no layout yet` refusals. NEITHER
    carries `error`/`unread`/`unparsed`, so v2926 counted both as readings, found `reverted` not
    True, and printed **"the lock fan kept its placement"**. MEASURED: a payload of
    `{"ok": false, "threw": "TypeError"}` produced `fanRevertedAt: []` and that exact sentence.

    The page's own `catch` exists to stop a crash and a keep looking alike — its comment says so in
    as many words — and the reader built to answer #53 reintroduced the collapse one layer up.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]

    ⚠ A MISSING `ok` IS NOT A PASS. Anything that is not explicitly `ok: true` is refused, so an
    older or unexpected shape reads UNMEASURED rather than clean.
    """
    if not isinstance(rec, dict):
        return "unread"
    if any(k in rec for k in ("error", "unread", "unparsed")):
        return "unread"
    if rec.get("ok") is True:
        return "reading"
    # ⚠⚠ v2931 — A CRASH AND A REFUSAL ARE DIFFERENT ANSWERS, and v2928 printed one sentence for
    # both. control_ui.html writes `{ok:false, threw:"..."}` when `_hrtFanFit` RAISES, and
    # `{ok:false, why:"the fan has no layout yet"}` when the solver RAN and declined — a timing or
    # layout miss, not an exception. v2928's rule was "ok present and not True -> threw", so the
    # heart told the operator THE SOLVER FAILED for what is really "the overlay opened before the
    # SVG had layout". The page's own comment says the two need different fixes.
    # Caught by the cross-family eye on v2928, one ship after it fixed the keep-lie.
    # [[unknown-stays-unknown]] [[label-outlived-referent]]
    if "threw" in rec:
        return "threw"
    if "ok" in rec:
        return "refused"
    return "unread"


def _fan_buckets(v):
    """Every width sorted into what it actually said. -> (reported, reading, threw, unread, refused)

    ⚠ v2936 — THE ARITY IS FIVE AND THE DOCSTRING SAID FOUR. v2931 split `refused` out of `threw`
    and updated every unpacker in the tree, but not the sentence that tells the next editor how
    many names to unpack — so following the docstring is a runtime ValueError. Caught by the
    cross-family eye, and it is the same [[label-outlived-referent]] class that ship just fixed
    on `_fan_counts`."""
    fan = (v.get("reports") or {}).get("heart-fan")
    if not isinstance(fan, dict) or not fan:
        # ⚠ v2928 — NOT `.get("heart-fan", {})`. The eye flagged a fabricated 0 here; measured, the
        # isinstance guard already caught two of its three cases, but the third — `heart-fan`
        # PRESENT AND EMPTY — really did publish `fanWidths: 0` beside `fanRevertedAt: None`, two
        # different answers to "did anybody measure". `not fan` closes it for good.
        return (None, [], [], [], [])
    rep = sorted(fan)
    by = {}
    for w in rep:
        by.setdefault(_fan_state(fan[w]), []).append(w)
    # ⚠⚠ A REFUSAL GETS ITS OWN BUCKET — it rides with NEITHER unread nor threw. None of the
    # three produced a placement, but they are three different reasons and `_fan_say` prints a
    # different sentence for each. This comment said "rides with unread" and the code has never
    # done that; an editor tidying the code to match would have deleted the declined-solver
    # sentence v2931 added. The eye caught the comment, not the code.
    return (rep, by.get("reading", []), by.get("threw", []),
            by.get("unread", []), by.get("refused", []))


def _fan_reverted(v):
    """Widths where the fan put everything back, or None if nothing was readable. -> list|None

    ⚠ None and [] ARE DIFFERENT ANSWERS. [] means every READABLE width kept its placement; None
    means no width produced a reading at all — absent, empty, failed, or thrown.
    Collapsing them is how #53 would read solved. [[unknown-stays-unknown]]
    """
    rep, reading, _threw, _unread, _refused = _fan_buckets(v)
    if rep is None or not reading:
        return None
    fan = v["reports"]["heart-fan"]
    return [w for w in reading if fan[w].get("reverted") is True]


def _fan_counts(v):
    """(reported, readable) — None when NOTHING WAS REPORTED; readable may legitimately be 0. -> tuple

    ⚠ v2931 — the v2928 docstring said "never 0" and the body returns 0 whenever heart-fan
    reported widths and none of them produced a reading. The eye judged it right: the published 0
    is the correct unknown-stays-unknown answer (widths WERE looked at, none was readable) and the
    DOCSTRING was the lie. A caller writing `readable or fallback` on the strength of that sentence
    would treat a measured zero as missing. [[label-outlived-referent]]
    """
    rep, reading, _t, _u, _r = _fan_buckets(v)
    return (None if rep is None else len(rep), None if rep is None else len(reading))


def _fan_say(v):
    """#53's answer in one sentence, or UNKNOWN said out loud. -> str

    ⚠⚠ v2926 — THE HEART DID NOT READ THE ONE THING BUILT TO ANSWER #53. v2924 added a per-width
    `report` tap and wrote `reports` into .render_verdict.json; MEASURED 2026-09-11, heart2.py
    contained the string "fanfit" ZERO times and "report" ZERO times. The fan could revert its
    placement at every photographed width and every automated supervisor still read OK.
    That is the identical shape this file already paid for at v2917 with `coverageStaleNodes` —
    a write whose only reader is its own writer. [[the-unjoined-end]] [[plumbing-with-no-tap]]

    ⚠ IT REPORTS, IT DOES NOT REFUSE. `state` keeps meaning "did every target report"; this rides
    beside it under its own name, for the same reason LAW 5 gives.
    """
    if not isinstance(v.get("reports"), dict):
        return ("whether the heart's lock fan kept or reverted its placement is UNKNOWN — this "
                "render verdict predates the per-width report tap, so nothing here measured it")
    rep, reading, threw, unread, refused = _fan_buckets(v)
    if rep is None:
        return ("whether the lock fan kept or reverted is UNKNOWN — heart-fan handed back no "
                "reading in the last render, which is not the same as a clean one")
    # ⚠ THE CAVEAT TRAVELS WITH THE NUMBER, or the heart re-creates the over-claim the tap was
    # rewritten to remove: the fan solves ONCE at open and never re-solves on resize, so a reading
    # filed under a width names where it was READ, never where it was SOLVED. [[stale-reading]]
    stale = (" (each reading names the width it was READ at; the fan solves once at open, so the "
             "width it was SOLVED at is UNKNOWN)")
    tail = ""
    if threw:
        tail += (" · the solver FAILED at %d width(s) (%s) — ok:false, which is not a placement"
                 % (len(threw), ", ".join(threw)))
    if refused:
        tail += (" · the solver RAN AND DECLINED at %d width(s) (%s) — ok:false with a reason, "
                 "which is a timing or layout miss and not a crash"
                 % (len(refused), ", ".join(refused)))
    if unread:
        tail += " · %d width(s) handed back no reading (%s)" % (len(unread), ", ".join(unread))
    if not reading:
        return ("the lock fan reported at %d width(s) and NONE produced a reading — UNMEASURED, "
                "not clean%s" % (len(rep), tail))
    rev = _fan_reverted(v) or []
    head = ("the lock fan REVERTED at %d of %d readable width(s): %s"
            % (len(rev), len(reading), ", ".join(rev))) if rev else \
           ("the lock fan kept its placement at all %d readable width(s)" % len(reading))
    return head + tail + stale


def surface_verdict(path=None):
    """What the LAST render run actually reported. -> dict

    v2859 — the heart counted GATES and never the SURFACES. render_check now records which targets
    reported; this reads that record and refuses to guess when it is absent or stale.
    `state` is one of: OK (a full run reported every target), PARTIAL (a subset run — cannot speak
    for the rest), UNMEASURED (no record, or unreadable). UNMEASURED IS NOT ZERO. [[stale-reading]]
    """
    # ⚠ `path` EXISTS SO A LAW CAN ASK THE REAL QUESTION. Without it the only way to test
    # "an absent verdict reads UNMEASURED" is to move the real file out from under a live
    # console, or to assert on the SHAPE of this function instead of its behaviour — and a
    # law that reads source instead of running the code is the weaker kind this repo keeps
    # having to strengthen. [[feedback-blind-fixture-green-gate]]
    p = path or os.path.join(HERE, ".render_verdict.json")
    if not os.path.exists(p):
        return {"state": "UNMEASURED", "why": "render_check has never written a verdict here — "
                                              "run `python3 tv/render_check.py`"}
    try:
        with io.open(p, encoding="utf-8") as fh:
            v = json.load(fh)
    except Exception as e:
        return {"state": "UNMEASURED", "why": "the render verdict would not parse (%s)"
                                              % type(e).__name__}
    rep = list(v.get("reported") or [])
    tot = int(v.get("totalTargets") or 0)
    age = None
    if v.get("ranAt"):
        age = int((time.time() * 1000 - float(v["ranAt"])) / 1000)
    return {"state": ("OK" if (v.get("full") and tot and len(rep) >= tot) else
                      "PARTIAL" if rep else "UNMEASURED"),
            "reported": len(rep), "totalTargets": tot, "ageS": age,
            "coverageMissing": int(v.get("coverageMissing") or 0),
            # ⚠⚠ v2917 (#72) — THE HEART CLAIMED TO SUPERVISE THIS AND DID NOT READ IT.
            # v2916 recorded the ratchet's own blind spot into .render_verdict.json and dropped the
            # heart join (P7) because `surfaces` had no UI consumer — then shipped FOUR assertions
            # that the heart was watching: render_check.py's two comments, this gate's header, and
            # LAW 7 itself. Found by the cross-family eye twenty minutes after it shipped.
            # MEASURED on his tree: .render_verdict.json carried `coverageStaleNodes: 30` while
            # `surface_verdict()` returned state OK / coverageMissing 0, and grep for a consumer of
            # coverageStale* outside render_check and its own gate returned ZERO. Thirty watched
            # nodes could vanish and every automated supervisor still read clean.
            # Moving a fact from scrollback into a file nobody opens is a better grave, not
            # supervision. [[the-unjoined-end]] [[label-outlived-referent]]
            # ⚠ IT REPORTS, IT DOES NOT REFUSE. LAW 5 of that gate is deliberate: a stale floor must
            # not by itself red a run, because a gate that is only ever red gets switched off. So
            # `state` keeps meaning "did every target report", and the slack rides beside it under
            # its own name with its own words.
            "coverageStaleNodes": (int(v["coverageStaleNodes"])
                                   if isinstance(v.get("coverageStaleNodes"), int) else None),
            # ⚠ THREE ANSWERS. None = an older render_check wrote this file and never measured
            # slack, which is UNKNOWN and not zero. False = there is no floor at all. True = a floor
            # exists, so a 0 beside it is MEASURED. [[unknown-stays-unknown]]
            "coverageFloorKnown": (bool(v["coverageFloorKnown"])
                                   if isinstance(v.get("coverageFloorKnown"), bool) else None),
            "coverageStaleSay": _stale_say(v),
            # ⚠⚠ v2926 (#53) — THE JOIN. Counts first so a law can assert on them, then the
            # sentence, because a number with no sentence is a number nobody acts on.
            # `fanRevertedAt` is None, never 0, when nothing was readable: UNMEASURED is not zero.
            # ⚠⚠ v2928 — TWO NAMES, BECAUSE THERE ARE TWO NUMBERS. v2926 published one `fanWidths`
            # = len(all keys) while `_fan_say` divided by len(readable). MEASURED: five widths all
            # returning {"error": …} gave `fanWidths: 5` beside a sentence saying NONE could be
            # read — a consumer dividing by the published denominator gets a different answer from
            # the published sentence. A name that promises the sentence's denominator must BE it.
            # [[zero-needs-a-denominator]] [[label-outlived-referent]]
            "fanWidthsReported": _fan_counts(v)[0],
            "fanWidthsReadable": _fan_counts(v)[1],
            "fanRevertedAt": _fan_reverted(v),
            "fanSay": _fan_say(v),
            "renderFailures": int(v.get("renderFailures") or 0)}


def gates_fingerprint(gates=None):
    """A content digest of every gate file. -> str

    ⚠⚠ v2862 — MTIME IS NOT A PORTABLE STALENESS SIGNAL, and the sandbox proved it. The first cut
    of the lock's staleness rule compared each gate file's mtime against the census `ranAt`. Correct
    on the machine that ran the prove — and WRONG everywhere else: safe_copy, a git checkout, CI and
    the Windows machine all stamp fresh mtimes, so every gate looks newer than the census, the lock
    closes on every surface, and `--prove` reported the lock gate UNPROVABLE because it was already
    red in its own sandbox. A rule that only holds in the tree that wrote it is not a rule.

    CONTENT survives copying. This is what "the instruments have not changed since they were proved"
    actually means. [[stale-reading]] [[the-harness-isolates-the-port-not-the-world]]
    """
    # ⚠⚠ v2869 — READ IT WHERE IT LIVES, NOT WHERE THE PROCESS HAPPENS TO STAND. `gate_files()`
    # returns BARE BASENAMES (it checks existence against HERE, so it is cwd-independent) and this
    # loop passed one straight to `_read_text`, which opens relative to the CURRENT DIRECTORY.
    # MEASURED: from the repo root, 273 of 273 gates read as UNREADABLE and the digest came out
    # 4d640d7d instead of 55330cec — so `_heart_says_watched()` called a freshly written census
    # STALE and `may()` refused EVERY lock, permanently, for any caller not standing in tv/.
    # The v2864 sentinel is what made it visible rather than silent, and it is exactly the class
    # v2862 replaced mtime to escape: a rule that only holds where it was run.
    # ⚠ The SENTINEL keeps the bare name on purpose — an absolute path differs per machine and
    # would undo the portability the content digest exists for. [[stale-reading]] [[copy-drift]]
    h = hashlib.sha256()
    for n, f in sorted(gates if gates is not None else gate_files()):
        h.update(n.encode("utf-8"))
        src = _read_text(f if os.path.isabs(f) else os.path.join(HERE, f))
        if src is None:
            # ⚠ v2864 — UNREADABLE IS NOT EMPTY, and a cross-family review caught the collapse:
            # hashing None as "" made every unreadable file digest identically to every empty one,
            # so the set of readable gates could change while the fingerprint held still. The path
            # goes into the sentinel so two different unreadable files differ. [[unknown-stays-unknown]]
            h.update(b"\x00UNREADABLE\x00" + f.encode("utf-8", "replace"))
            continue
        h.update(hashlib.sha256(src.encode("utf-8", "replace")).digest())
    # ⚠⚠ AND THE PROVER ITSELF. Same review: the digest covered gate FILES only, so a change to
    # gate_files(), to how the sabotage is injected, or to any decision heart2 makes about RED would
    # leave the fingerprint identical and the lock would still call a stale proof current. The proof
    # is only as true as the thing that produced it, so this file is folded in too.
    # [[the-unjoined-end]]
    _self = _read_text(os.path.join(HERE, "heart2.py"))
    h.update(hashlib.sha256((_self or "").encode("utf-8", "replace")).digest())
    return h.hexdigest()[:32]


def gate_shas(gates=None):
    """#99 — each gate file's OWN content digest: the per-gate half of gates_fingerprint(). -> {name: sha | None}

    None = the file would not read. UNKNOWN, never an empty file's digest - so an unreadable gate is owed a proof,
    never counted as proved for a file nobody could read. [[unknown-stays-unknown]]"""
    out = {}
    for n, f in (gates if gates is not None else gate_files()):
        src = _read_text(f if os.path.isabs(f) else os.path.join(HERE, f))
        out[n] = None if src is None else hashlib.sha256(src.encode("utf-8", "replace")).hexdigest()[:16]
    return out


def blind_rule_owed(state):
    """REG-2355 — the BLIND gates a census filed under an older BLIND_RULE and has not judged since. -> set (pure)

    A census stamped with this rule carries what is left by name (`blindRuleOwed`); one from before it - or from an
    older rule - owes its whole BLIND list. Asked by slice_owed() here and by self_prove.census_state(), one answer."""
    if not isinstance(state, dict):
        return set()
    if state.get("blindRule") == BLIND_RULE:
        return set(state.get("blindRuleOwed") or [])
    return set(state.get("blind") or [])


def slice_owed(gates=None, state=None, env_path=None):
    """#99 — which gates that DECLARE a proof this census has not proved against the file on disk now. -> dict

    {"owed": [(name, n_proofs)], "declared": int, "covered": int, "why": str}. `state` is a parsed census; None reads
    STATE. An absent census owes every declaring gate; one that will not parse owes them all too and SAYS so - the
    slices then rebuild it, and heart2 refuses to write over a file it cannot read, so that case is named, not hidden.
    A census from before per-gate digests (no `gateShas`) owes everything once: nothing in it can say which gate
    files changed since it ran."""
    gates = gates if gates is not None else gate_files()
    why = ""
    if state is None:
        state = {}
        if os.path.exists(STATE):
            try:
                with io.open(STATE, encoding="utf-8") as fh:
                    state = json.load(fh)
            except Exception as e:
                state, why = {}, "the census would not parse (%s)" % type(e).__name__
    recorded = state.get("gateShas") if isinstance(state, dict) else None
    recorded = recorded if isinstance(recorded, dict) else {}
    _rule_blind = blind_rule_owed(state)
    shas = gate_shas(gates)
    owed, declared = [], 0
    for n, f in gates:
        proofs = red_proofs_in(f)
        if not proofs:
            continue
        declared += 1
        if not shas.get(n) or recorded.get(n) != shas.get(n):
            owed.append((n, len(proofs)))
        # REG-2355 — and a BLIND judged under an older BLIND_RULE, though its file is unchanged: a gate is otherwise owed
        # only when its OWN file changes, so a fixed rule would never reach the verdicts the old one filed (Dean's 53).
        elif _rule_blind and n in _rule_blind:
            owed.append((n, len(proofs)))
    # v3862 (item 4) - a PENDING environment re-prove owes every declaring gate not yet proved since the change
    _er = env_reprove_state(state if isinstance(state, dict) else {}, gates, path=env_path)
    if _er and _er.get("owed"):
        _have_n = {n for n, _k in owed}
        _np = dict((n, len(red_proofs_in(f) or [])) for n, f in gates)
        owed.extend((n, _np.get(n, 0)) for n in _er["owed"] if n not in _have_n)
        why = why or ("this PC's environment changed (%s): %d gate(s) proved again since" % (
            env_change_words(_er), len(_er["owed"])))
    owed.sort(key=lambda t: t[0])
    return {"owed": owed, "declared": declared, "covered": declared - len(owed),
            "why": why or ("%d of %d declaring gate(s) proved for the files on disk" % (declared - len(owed), declared))}


def pixel_gates(gates=None, unclassified=None):
    """The gates that actually LOOK AT PIXELS, by their IMPORTS. -> set[str]

    v2858 — ONE NUMBER WAS HIDING A 93/7 SPLIT. Konyo: "when we hit 100% on heart 2.0 its also a
    VISUAL PASS right? like its not just backend". MEASURED the moment he asked: 269 gates, only TEN
    import render_check or playwright, so 100% on the single number would be ~96% backend — true as
    a count and a lie as a label. [[label-outlived-referent]]

    ⚠ IMPORTS, NOT A TEXT SCAN. The first cut grepped for 'render_check' / 'playwright' /
    '.render_shots' and answered 18, because prose and comments naming the harness counted as
    looking at pixels. Parsing answers 10. [[source-reading-guard]]

    ⚠⚠ v2860 — IT SWALLOWED THE GATES IT COULD NOT READ, and a cross-family review caught it. Both
    the unreadable case and the SyntaxError case did a bare `continue`, so a gate that really does
    import render_check but was momentarily unreadable — permissions, a half-written checkout, a
    syntax error the day the census ran — silently left the pixel set and landed in the BACKEND
    count. The owner would read an inflated backend share, and a later "100%" would quietly include
    a visual gate nobody classified. A failed read handed back as data, inside the thing that
    measures the heart. `unclassified` collects those names so the census can SAY so.
    [[unknown-stays-unknown]]

    ⚠ AND IT UNDER-COUNTS, IN THE DANGEROUS DIRECTION. Same review: top-level Import/ImportFrom
    names miss importlib, __import__, exec/compile, and any gate that reaches the renderer through
    a helper instead of importing it. So pixelTotal is a FLOOR — the visual share is at best this
    good and possibly worse, never better. Recorded because this number answers "is 100% also a
    visual pass", and a bias that flatters that answer is the one bias that must not go unsaid.
    """
    out = set()
    _unk = unclassified if unclassified is not None else []
    for n, f in (gates if gates is not None else gate_files()):
        # ⚠ v2869 — SAME BARE-NAME BUG AS gates_fingerprint, same cause: gate_files() hands back
        # basenames and _read_text opens relative to cwd. From the repo root this made every gate
        # UNREADABLE, so pixelTotal would read 0 and pixelUnclassified 273 — a census that answers
        # "how much of this is pixels" with a number produced by the reader's working directory.
        src = _read_text(f if os.path.isabs(f) else os.path.join(HERE, f))
        if src is None:
            _unk.append(n)                # UNREADABLE is not "backend"
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            _unk.append(n)                # UNPARSEABLE is not "backend" either
            continue
        mods = set()
        for x in ast.walk(tree):
            if isinstance(x, ast.Import):
                for a in x.names:
                    mods.add(a.name.split(".")[0])
            elif isinstance(x, ast.ImportFrom):
                if x.module:
                    mods.add(x.module.split(".")[0])
        if mods & {"render_check", "playwright"}:
            out.add(n)
    return out


#: #42 — what starts a browser: the harness module in tv/ and the one package outside it.
_RENDERERS = ("render_check", "playwright")


def _imported_names(tree):
    """#42 — every top-level module name one parsed file can import. -> set[str]

    `import a.b` / `from a.b import c` anywhere in the file (a lazy import inside a function starts the same browser the
    day that function runs), `from tv import x` as x, and `__import__("x")` / `importlib.import_module("x")` when the
    name is a literal. A name built at run time is not seen - the same floor pixel_gates states, one level down."""
    out = set()
    for x in ast.walk(tree):
        if isinstance(x, ast.Import):
            for a in x.names:
                out.add(a.name.split(".")[0])
        elif isinstance(x, ast.ImportFrom) and x.module:
            head = x.module.split(".")[0]
            out.add(head)
            if head == "tv":
                out.update(a.name.split(".")[0] for a in x.names)
        elif (isinstance(x, ast.Call) and x.args and isinstance(x.args[0], ast.Constant)
              and isinstance(x.args[0].value, str)):
            fn = x.func
            called = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None
            if called in ("__import__", "import_module"):
                out.add(x.args[0].value.split(".")[0])
    return out


def browser_gates(gates=None, tv_dir=None, unclassified=None):
    """#42 — the gates whose IMPORT GRAPH reaches a browser (render_check / playwright), however many helpers deep.
    -> set[str]

    ⚠ pixel_gates READS ONE FILE, AND THE ONE-BROWSER LOCK WAS BUILT ON IT. It answers "does this gate import the
    harness itself", which misses a gate that reaches it through a helper - test_the_rails_fold_is_a_chevron_not_a_dot
    does `import test_the_character_builder_fits_at_every_width as FT; RC = FT.RC` and calls RC._chrome_up(), so at push
    time it could start a second Chrome beside a width law while the lock said one. Found by the adversarial review of
    #42. The lock set is the CLOSURE: follow every name the gate imports that is a module in tv/ (tv/<name>.py), then
    every name those import, and so on; the gate is in the set when any of them imports render_check or playwright.

    ⚠ UNKNOWN GOES UNDER THE LOCK. A gate - or a helper anywhere in its closure - that cannot be read or parsed may
    reach a browser and nobody can say it does not: it is in the set (the safe side costs time, never a second Chrome)
    and its name goes into `unclassified`. Over-inclusion is the only error this may make on purpose.

    CACHED PER RUN: each tv/ file is parsed at most once per call, however many gates share it, and only the files some
    gate actually reaches are parsed. `tv_dir` lets the law build its fixture modules in a temp dir. [[the-unjoined-end]]
    [[unknown-stays-unknown]]"""
    d = tv_dir or HERE
    _unk = unclassified if unclassified is not None else []
    try:
        local = set(f[:-3] for f in os.listdir(d) if f.endswith(".py"))
    except OSError:
        # ⚠ NOT an empty tree: read as "no helpers" it would follow nothing and let every helper-reached browser out of
        # the lock. Nobody can say what the gates import, so each one is UNKNOWN below - locked and named.
        local = None
    parsed = {}                       # module -> set of names it imports | None (unreadable / unparseable)

    def _names(mod, path=None):
        if mod not in parsed:
            src = _read_text(path or os.path.join(d, mod + ".py"))
            try:
                parsed[mod] = None if src is None else _imported_names(ast.parse(src))
            except (SyntaxError, ValueError):      # ValueError: a NUL byte in the source - unparseable all the same
                parsed[mod] = None                  # UNKNOWN, never "imports nothing": the caller locks it and names it
        return parsed[mod]

    out = set()
    for n, f in (gates if gates is not None else gate_files()):
        path = f if os.path.isabs(f) else os.path.join(d, f)
        if not os.path.exists(path):
            # ABSENT is not UNREADABLE: a gate file that is not there runs nothing, so it starts no browser (and its
            # proof is refused on its own line: "the gate file is not in the sandbox"). Every helper followed below
            # exists - they come from the directory listing.
            continue
        start = os.path.basename(path)[:-3] if path.endswith(".py") else os.path.basename(path)
        seen, stack, verdict = set(), [(start, path)], (False if local is not None else "unknown")
        while stack and not verdict:
            mod, p = stack.pop()
            if mod in seen:
                continue
            seen.add(mod)
            names = _names(mod, p)
            if names is None:
                verdict = "unknown"
                break
            if names & set(_RENDERERS):
                verdict = True
                break
            for dep in names & local:
                stack.append((dep, None))
        if verdict:
            out.add(n)
            if verdict == "unknown":
                _unk.append(n)
    return out


def _read_text(path):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return None


def gate_files(say=print):
    # ⚠ `say` IS A PARAMETER HERE, NOT A GLOBAL. heart2 threads its printer through
    # (make_sandbox(say=print), prove(..., say=print)); there is no module-level `say`.
    # v2882 added the dropped-gate warning below WITHOUT this parameter, so the one line that
    # exists to make a silent omission loud would have raised NameError the first time a gate
    # was actually dropped — a warning that cannot fire, inside the fix for a warning that was
    # never written. Caught because --triage hit the same mistake and crashed immediately.
    # [[plumbing-with-no-tap]] [[feedback-blind-fixture-green-gate]]
    """Every registered gate that is a python test file here. -> [(name, filename)]"""
    out, _dropped = [], []
    try:
        import run_gates
    except Exception as e:
        print("  run_gates will not import: %s" % e)
        return out
    for g in getattr(run_gates, "GATES", []):
        # ⚠ THE FIELD IS `argv`, NOT `cmd`. The first cut guessed `cmd`, found nothing, and
        # printed "0 gates" — a zero produced by my own parser, wearing the clothes of a
        # measurement. Every percentage under it would have been 0.0% of nothing.
        # [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
        cmd = list(getattr(g, "argv", None) or getattr(g, "cmd", None) or [])
        fn = None
        for part in cmd:
            if isinstance(part, str) and part.endswith(".py") and os.path.basename(part) != "":
                base = os.path.basename(part)
                if os.path.exists(os.path.join(HERE, base)):
                    fn = base
                # ⚠⚠ v2882 — A GATE WHOSE FILE IS NOT IN tv/ WAS DROPPED SILENTLY, AND COUNTED
                # NOWHERE. `visual-lock` runs REPO/visual_lock_invariant.py; the check above only
                # looked in HERE, so it failed and the gate vanished from the heart's scope with no
                # line saying so. Measured: run_gates registers 279 gates, the heart reported 278 —
                # and "0 blind of 278" read as "every gate is accounted for" while one was not even
                # asked about. The heart's own premise is that the instruments must watch
                # themselves; a census that quietly omits a row is the first thing that premise
                # forbids. Root files are addressed ".."-relative so every consumer keeps working:
                # red_proofs_in and _run_gate both os.path.join(<tv>, filename), which resolves to
                # the repo root, and make_sandbox places the file there.
                # [[unknown-stays-unknown]] [[zero-needs-a-denominator]] [[heart-v2-instruments-watch-themselves]]
                elif os.path.exists(os.path.join(REPO, base)):
                    fn = os.path.join("..", base)
        if fn:
            out.append((getattr(g, "name", fn), fn))
        else:
            _dropped.append(getattr(g, "name", "?"))
    if _dropped:
        say("  ⚠ %d registered gate(s) have no python file this heart can read, so they are NOT in "
            "the census below — UNKNOWN, not clean: %s" % (len(_dropped), ", ".join(_dropped)))
    return out


#: #172 phase C - ONE PARSE PER GATE FILE PER STAMP, for every caller in a process. The console asked this for all 1,237
#: gate files twice (slice_owed for the self-arming owed list, health_engine for the attack tally, each with its own memo or
#: none) - 2,473 parses in its own heap. Kept per path on (mtime_ns, size); an unreadable file (None) is not kept.
_RP_MEMO = {}


def red_proofs_in(filename):
    """The RED_PROOF list a gate file declares, read WITHOUT importing it.

    Parsed rather than imported: importing 247 test modules to ask a question about their source
    would execute 247 modules' import-time side effects, and several of them read his live console.
    [[source-reading-guard]]
    #172 phase C - kept per file stamp, and on a console answered from the list a short-lived child derived
    (audit_child.red_proofs_for), so the console's own heap parses none of them; anything else parses here as before.
    """
    p = os.path.join(HERE, filename)
    try:
        st = os.stat(p)
        key = (st.st_mtime_ns, int(st.st_size))
    except OSError:
        key = None
    if key is not None:
        hit = _RP_MEMO.get(p)
        if hit is not None and hit[0] == key:
            return hit[1]
        try:
            import audit_child as _ac
            got = _ac.red_proofs_for(filename, key)
        except Exception:
            got = None
        if got is not None:
            _RP_MEMO[p] = (key, got)
            return got
    import ast
    try:
        with io.open(p, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except Exception:
        return None
    out = _red_proofs_of_tree(tree)
    if key is not None and out is not None:
        _RP_MEMO[p] = (key, out)
    return out


def _red_proofs_of_tree(tree):
    """red_proofs_in's reader, on a tree already parsed - #42 reads a gate's RED_PROOF as the push BASE holds it through
    this same function, never a second copy of the rule below. [[copy-drift]]"""
    import ast
    # ⚠⚠ #220 — IT RETURNED INSIDE THE FIRST MATCHING ASSIGN. Two defects from one early return:
    # (1) the eye on v3476: a literal list followed by an unreadable one landed in `have` (its first
    # list's proofs ran) AND in red_proof_unreadable's bucket, so prove()'s "do not" went -1 and the
    # warning said none of it had run; (2) MEASURED 2026-09-24, the live one the eye did not name:
    # test_the_ledger_cannot_lie_about_what_it_saw.py bound RED_PROOF twice — 1 proof at line 82,
    # 11 at line 519 — and this proved the FIRST, which `import` overwrites. The 11 had never run.
    # Now ONE walker for every caller: any unreadable binding -> None (the declaration is
    # unreadable as a whole, exactly what red_proof_unreadable says); otherwise the LAST binding,
    # which is what the module holds. The census refuses more than one binding outright.
    vals = []
    for node in _red_proof_bindings(tree):
        try:
            vals.append(ast.literal_eval(node.value))
        except Exception:
            return None
    if not vals:
        return None
    return _normalise_proofs(vals[-1])


def _red_proof_bindings(tree):
    """Every top-level binding of RED_PROOF — `=` and `x: T = ...` — in file order. -> [ast node]"""
    import ast
    out = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "RED_PROOF" for t in node.targets):
                out.append(node)
        elif isinstance(node, ast.AnnAssign):
            if (isinstance(node.target, ast.Name) and node.target.id == "RED_PROOF"
                    and node.value is not None):
                out.append(node)
    return out


def red_proof_binding_count(filename):
    """#220 — how many top-level RED_PROOF bindings a gate file has. -> int | None (will not parse)

    More than one is a malformed declaration: only the LAST exists at import, so an author who
    wrote two lists believes proofs run that never do. The census refuses it."""
    import ast
    p = os.path.join(HERE, filename)
    try:
        with io.open(p, encoding="utf-8") as fh:
            return len(_red_proof_bindings(ast.parse(fh.read())))
    except Exception:
        return None


def red_proof_unreadable(filename):
    """v3473 — does this file DECLARE a RED_PROOF the prover cannot read? -> True | False | None

    ⚠⚠ red_proofs_in() answers None for FOUR different states — no file, no declaration, a file
    that will not parse, and a list ast.literal_eval refuses — and every caller reads None as "this
    gate declares no proof". MEASURED 2026-09-24: test_a_cut_off_gate_set_is_not_a_verdict declared
    eleven proofs whose `file` was the NAME `WF_REL`; literal_eval threw, the prover printed
    "0 declare a red-proof", and not one of the eleven had ever run. Once literal, all eleven were
    PROVEN. An unreadable declaration is not an absent one. [[unknown-stays-unknown]]
    None means the FILE would not parse, which is UNKNOWN too — never False.
    """
    import ast
    p = os.path.join(HERE, filename)
    try:
        with io.open(p, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except Exception:
        return None
    # ⚠ v3476 — EVERY top-level assignment, `x: T = ...` included. The v3473 cut returned on the
    # FIRST Assign to RED_PROOF, so a literal list followed by a `WF_REL` one read as readable and the
    # unreadable one was invisible; an AnnAssign was never looked at. Found by the eye on v3473.
    for node in _red_proof_bindings(tree):    # #220 — the same walker red_proofs_in uses
        try:
            ast.literal_eval(node.value)
        except Exception:
            return True
    return False


def _normalise_proofs(raw):
    """Every declared proof as the dict `_prove_one` reads. -> [dict]

    ⚠⚠ TWO SHAPES WERE IN THE TREE AND THE PROVER COULD ONLY READ ONE, SO THE WHOLE LOOP DIED.
    374 gates declare `RED_PROOF` as dicts; **12 declare 4-tuples** `(file, find, replace,
    breaks)`. `_prove_one` does `pr.get("file")` with no isinstance check, and `prove()`'s loop is
    `try: ... finally:` with NO `except` — so the first tuple raised AttributeError straight out
    of `prove()`, **`_write_state(results)` never ran**, and `_heart2_census()` in control_app.py
    went on reading a file nothing had refreshed.

    So the organ whose entire purpose is asking "can my own gates still go red" aborted on gate
    number one of twelve, and reported through a census it had stopped writing. MEASURED
    2026-09-17: 32 proofs across 12 gates, every one of arity 4, none of them ever executed.

    ⚠ NORMALISE AT THE READER, NOT AT THE PROVER. Both the engine and every law that inspects
    proofs go through this function, so a second shape can never again be legal for one reader and
    unreadable to another. The tuple's 4th slot names the law that must break, which is what the
    dict calls `why`; `matches` is absent from the tuple form and stays None — UNKNOWN, so a
    tuple proof can never claim a match count nobody wrote. [[the-unjoined-end]]
    [[unknown-stays-unknown]] [[copy-drift]]
    """
    out = []
    for pr in (raw or []):
        if isinstance(pr, dict):
            out.append(pr)
            continue
        if isinstance(pr, (tuple, list)) and len(pr) == 4:
            out.append({"file": pr[0], "find": pr[1], "replace": pr[2],
                        "why": pr[3], "matches": None})
            continue
        # a shape nobody has taught this reader: keep it, so the well-formedness law SEES it and
        # says so, rather than it vanishing here and reading as "no proof declared".
        out.append({"file": None, "find": None, "replace": None,
                    "why": "unreadable proof shape: %r" % (pr,), "matches": None})
    return out


# ── the sandbox ──────────────────────────────────────────────────────────────────────────────
def proof_needs_in(filename):
    """The data a gate's proof needs beside the source. -> [relative path under tv/]

    ⚠⚠ v2888 — A GATE WHOSE SUBJECT IS ABSENT SKIPS, AND A SKIP IS NOT A PASS.
    test_chronicle_template came back BLIND with the reason "ALL 12 law(s) SKIPPED in the sandbox —
    the tamper was never judged". That was not a bad anchor: every one of its 12 laws is decorated
    `@unittest.skipUnless(_HAVE_FOOTAGE)`, MEASURED 12 of 12, so with no footage the whole gate is a
    no-op that exits 0. safe_copy deliberately leaves tv/'s 5.8 GB of footage behind — correctly,
    that rule exists because copying it hit ENOSPC once — so the sandbox could never judge it.
    This is the narrow door: a gate names the ONE data path its proof needs, by hand, and only that
    path is brought across. Read by AST, never imported. [[regression-guard]] [[zero-needs-a-denominator]]
    """
    # ⚠⚠ None MEANS "I COULD NOT READ THIS". IT NEVER MEANS []. The first cut answered [] on a
    # parse failure and the swallow ratchet caught it ON CI THE SAME DAY — RANK 1, "a failed read
    # handed back as DATA", baseline 74 -> 75, `tv/heart2.py 0 -> 1`. [] says "this gate declares
    # no needs"; a file that will not parse says nothing at all, and those are opposite facts. Get
    # it wrong and a gate is silently deprived of the data its proof requires, then reported BLIND
    # for a reason that names none of it. A non-.py target still answers [] and that is correct:
    # PROOF_NEEDS is a python declaration, so a file that cannot hold one genuinely declares none.
    # [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    p = os.path.join(REPO, "tv", filename) if not os.path.isabs(filename) else filename
    if not os.path.isfile(p) or not p.endswith(".py"):
        return []
    try:
        with io.open(p, encoding="utf-8", errors="replace") as _fh:      # closed: this ran ~700 times per prove unclosed
            tree = ast.parse(_fh.read())
    except Exception:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "PROOF_NEEDS" for t in node.targets):
            continue
        try:
            v = ast.literal_eval(node.value)
        except Exception:
            return None            # it DECLARES needs and they cannot be read — UNKNOWN, not none
        return [str(x) for x in v] if isinstance(v, (list, tuple)) else []
    return []


# ⚠⚠ 2026-09-26 — A KILLED PROVER LEFT ITS SANDBOX BEHIND, ELEVEN TIMES. Every sandbox is removed in a `finally`,
# and a `finally` never runs when the process is killed by a signal: the pre-push gate's bound, a `perl alarm`, a
# closed terminal. MEASURED that morning: 11 heart2.* repo copies in the temp dir, Sep 23 -> Sep 26, one per
# interrupted run, the newest from a proof I bounded at 50 minutes myself. So every sandbox is REGISTERED the moment it
# exists and carries its owner's pid; SIGTERM / SIGALRM / SIGHUP remove the registered ones before the process dies; and
# every run first sweeps a heart2.* sandbox whose owner is dead (or, written before the owner file existed, a day old).
# A sandbox whose owner is ALIVE is never touched - it is another prover, mid-run. [[i-own-everything-i-start]]
_SANDBOXES = set()
_SANDBOX_OWNER = ".heart2-owner"
SANDBOX_STALE_S = 24 * 3600


def _pid_alive(pid):
    # ⚠⚠ #50 (REG-1447) — os.kill(pid, 0) IS A CTRL-C ON WINDOWS (signal 0 == CTRL_C_EVENT), not a probe.
    # Now that every PC proves itself, this runs on Windows: ask the way control_app does. An import
    # failure answers ALIVE - keeping a sandbox is safe, removing a live prover's sandbox is not.
    if os.name == "nt":
        try:
            import self_prove as _sp
            return _sp.pid_alive(pid)
        except Exception:
            return True
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True                          # it exists, it is simply not ours to signal
    except (OSError, ValueError, TypeError):
        return False
    return True


#: Off the Mac there is no free clone, so a need is COPIED - and only below these sizes. Above them the gate
#: stays UNPROVABLE, which is honest, rather than a prover filling his disk one sandbox at a time.
_NEED_COPY_MAX_FILE = 50 * 1024 * 1024
_NEED_COPY_MAX_TREE = 200 * 1024 * 1024


def _tracked_dirty():
    """v3850 (REG-2630 on Dean's console, 2026-10-31) - THE ONE QUESTION 'IS THIS CHECKOUT ITS HEAD?' -> (ok, porcelain).

    The export refused on Dean's PC with ` M tv/.status_worst.json` as the only edit: a record the console rewrites
    itself, already forgiven by self_prove.tracked_edits for every other reader of a dirty tree (REG-1837/1898). Every
    heart2 dirty check (shard manifest, export, import, check) asks this door. A rule that cannot be asked keeps the
    raw rows (dirty, the safe direction)."""
    ok, out = _git("status", "--porcelain", "--untracked-files=no")
    if not ok:
        return ok, out
    try:
        import self_prove as _sp
        lines, _why = _sp.tracked_edits(out)
    except Exception:
        lines = None
    if lines is None:
        return ok, out
    return ok, "\n".join(lines)


def _git_free_env(**extra):
    """REG-2396 - THE ENVIRONMENT OF EVERY PROCESS HEART2 STARTS: this process's, with EVERY GIT_* variable removed, plus
    `extra`. -> dict. One definition, run_gates.git_free_env (law_env applies it to every law run there and here).

    ⚠⚠ heart2 dropped GIT_* in 2 routines - 5 of its 9 spawn calls (found by the cross-family review of Push A2): the
    law runs themselves (_run_gate_once), its own key questions (`git -C REPO ...`, which a leaked GIT_DIR beats) and
    the APFS cp inherited whatever the caller had. So a prove started from an OLD hook - a push runs the hook in his
    MAIN checkout, the one origin/main had - or by hand inside one ran every law under the pointer at the real repo,
    and keyed its proofs on another tree's files. The new hook unsets it first; this holds whoever the caller is."""
    import run_gates as _rg
    return _rg.git_free_env(None, **extra)


def _bring_across(src, dst, need, say):
    """Place one PROOF_NEEDS item in a sandbox. Never escapes the sandbox, never fills the disk.

    ⚠⚠ #50 (REG-1448) — THIS WAS `cp -c -R` ON EVERY PLATFORM, AND `cp` DOES NOT EXIST ON WINDOWS. Every
    need raised FileNotFoundError there, so no sandbox on the ALT carried `.git` or the spec file, and the
    laws that read them SKIPPED through their own sabotage - `test_eye_declares_reach` read BLIND on the
    ALT while it goes red on the Mac. Now that every PC proves itself (REG-1447), that is a lock held shut
    on every Windows PC by the prover's own plumbing.
    The Mac keeps the APFS clone, byte for byte. Elsewhere: `.git` (1.8 GB on his Mac) becomes a private
    `git clone --shared` (_share_history) - the objects are BORROWED read-only through alternates, the refs and
    the index are the sandbox's own, so nothing a law runs in there can write into the real repository; its
    index is rebuilt from HEAD, which on an installed console is the working tree. Anything else is copied only
    under the size caps above.
    """
    if sys.platform == "darwin":
        _rc = subprocess.run(["cp", "-c", "-R", src, dst],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=_git_free_env()).returncode
        if _rc != 0:      # not APFS, or clones unavailable — say so rather than silently copying GBs
            say("  could not CLONE %r (cp -c exit %s) — not copying it by hand; the gate stays "
                "UNPROVABLE rather than risking the disk" % (need, _rc))
            return
        if os.path.basename(os.path.normpath(src)) == ".git" and os.path.isdir(dst):
            # REG-2397 - THE MAIN CHECKOUT'S HISTORY ARRIVES AS A WHOLE COPY OF ITS .git, REMOTES INCLUDED: its origin
            # is GitHub (the PUBLIC repo) and a `git push` a law made in the sandbox would have gone there. Shut every
            # remote's push the way _share_history shuts a clone's; a copy whose push cannot be shut is not kept.
            if not _shut_push(dst, say):
                _rmtree_hard(dst)
                say("  the sandbox's copy of %r could not have its push shut — not kept, so gates that read it stay "
                    "UNPROVABLE" % need)
        return
    if os.path.basename(os.path.normpath(src)) == ".git" and os.path.isdir(src):
        _share_history(os.path.dirname(os.path.normpath(src)), dst, say)
        return
    if os.path.isfile(src):
        if os.path.getsize(src) > _NEED_COPY_MAX_FILE:
            say("  PROOF_NEEDS %r is too large to copy without a clone — the gate stays UNPROVABLE" % need)
            return
        shutil.copy2(src, dst)
        return
    total = 0
    for _r, _ds, _fs in os.walk(src):
        for _f in _fs:
            try:
                total += os.path.getsize(os.path.join(_r, _f))
            except OSError:
                pass
            if total > _NEED_COPY_MAX_TREE:
                say("  PROOF_NEEDS %r is over %d MB — not copied without a clone; the gate stays UNPROVABLE"
                    % (need, _NEED_COPY_MAX_TREE // (1024 * 1024)))
                return
    shutil.copytree(src, dst)


#: REG-2364 - where a sandbox history's PUSH url points: a path inside its own git dir that is never a repository, so
#: a push from a sandbox fails at once instead of writing the checkout it was cloned from.
_NO_PUSH = "no-push-from-a-sandbox"


def _shut_push(git_dir, say):
    """REG-2364 / REG-2397 - EVERY REMOTE of the history at `git_dir` (a sandbox's own .git) gets a push url that is no
    repository. -> bool (False: a remote could not be read or shut - the caller then keeps no history)

    A clone's origin is the checkout it was cloned from (REG-2364). A Mac sandbox's copy of the main checkout's .git keeps
    HIS remotes, and its origin is GitHub - the PUBLIC repo (REG-2397). Either way a `git push` a law made in the sandbox
    would write a real repository. A remote's push url beats its url for a push (and a remote that has one ignores
    url.*.pushInsteadOf), so each one points at a path inside the sandbox's own git dir that is never a repository, and
    the push fails at once. Asked through --git-dir with no GIT_* variable: nothing but the sandbox's config is written."""
    env = _git_free_env(GIT_OPTIONAL_LOCKS="0")
    git = ["git", "--git-dir=" + git_dir]
    try:
        r = subprocess.run(git + ["config", "--get-regexp", r"^remote\..+\.(url|pushurl)$"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
        if r.returncode not in (0, 1):            # 1: no remote at all - nothing to shut
            say("  the sandbox's git remotes could not be read (git config exit %s)" % r.returncode)
            return False
        names = sorted(set(m.group(1) for m in (re.match(r"remote\.(\S+)\.(?:url|pushurl)(?:\s|$)", ln)
                                                 for ln in (r.stdout or "").splitlines()) if m))
        for name in names:
            shut = subprocess.run(git + ["config", "--replace-all", "remote.%s.pushurl" % name,
                                         os.path.join(git_dir, _NO_PUSH)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=60, env=env)
            if shut.returncode != 0:
                say("  the sandbox's remote %r could not have its push shut (git config exit %s)"
                    % (name, shut.returncode))
                return False
        return True
    except (OSError, subprocess.SubprocessError) as e:
        say("  the sandbox's git remotes could not be shut (%s)" % type(e).__name__)
        return False


def _share_history(work_tree, dst, say):
    """A PRIVATE git history of `work_tree`, placed at `dst` (a sandbox's `.git`). -> True when the sandbox holds one.

    `git clone --shared --no-checkout`: the objects are BORROWED read-only through alternates (nothing copied), the
    refs, the index and the config are the sandbox's own, and HEAD is work_tree's HEAD - so a law reads the history
    being proved, and nothing it runs in there can write the real repository. Off the Mac a `.git` directory comes
    this way (REG-1448); on every platform a linked worktree's `.git` POINTER does (REG-2364, make_sandbox).

    ⚠⚠ REG-2364 - NO GIT_* VARIABLE REACHES THESE CALLS. Git exports GIT_DIR into every hook and GIT_DIR beats cwd=.
    MEASURED on a fixture worktree: the `read-tree HEAD` below, run under a leaked GIT_DIR, rewrote the REAL worktree's
    index (its staged entry gone), and a leaked GIT_WORK_TREE makes the clone itself refuse. A prover started from a
    hook - the old one, or one run by hand inside it - carries them. [[feedback-fixtures-never-touch-live-data]]
    ⚠ AND THE CLONE'S `origin` IS THE REAL CHECKOUT, so a `git push` from the sandbox would write its refs - a door of
    the same kind as the leaked GIT_DIR that put two fixture commits on his push branch on v3783. The push url is
    pointed at a path that is no repository, and a history whose push could not be shut is not kept.
    """
    env = _git_free_env(GIT_OPTIONAL_LOCKS="0")
    tmp = dst + ".shared"
    placed = False
    try:
        import git_quiet as _gq        # v3866 - a pythonw child's plain git opened a terminal over his game
        r = _gq.run(["git", "clone", "-q", "--shared", "--no-checkout", work_tree, tmp],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=env)
        if r.returncode != 0:
            say("  could not share the git history into the sandbox (git clone --shared exit %s) — gates "
                "that read it stay UNPROVABLE" % r.returncode)
            return False
        os.replace(os.path.join(tmp, ".git"), dst)
        placed = True
        _gq.run(["git", "read-tree", "HEAD"], cwd=os.path.dirname(dst),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, env=env)
        if not _shut_push(dst, say):
            _rmtree_hard(dst)
            say("  the sandbox's git history could not have its push shut — not kept, so gates that read it stay "
                "UNPROVABLE")
            return False
        return True
    except (OSError, subprocess.SubprocessError) as e:
        if placed:
            _rmtree_hard(dst)
        say("  could not share the git history into the sandbox (%s) — gates that read it stay UNPROVABLE"
            % type(e).__name__)
        return False
    finally:
        _rmtree_hard(tmp)


def _drop_run_records(dest, keep, say):
    """REG-2365 — the copied repo at `dest` loses every LIVE run record. -> {repo-relative path: what was done}

    A run record is what a RUN writes into the tree it grades: heart2's own (_SELF_RECORDS, all in tv/) and the gate
    runs' (suite_verdict.RUN_RECORDS - read from there, never restated). One that HEAD does not track is removed; one it
    tracks becomes HEAD's blob, restored by the sandbox's OWN private history (the `../.git` two gates declare, brought
    by make_sandbox as a clone), so no Python write and no git call ever reaches the real repo. A record a gate declares
    in PROOF_NEEDS (`keep`) stays: that law asked for it, and its key holds it.
    ⚠⚠ WHAT IT COST. Since REG-2361 the hook's tv suites run BEFORE the proving stage, in the tree heart2 then copies.
    One of them (test_control's TestV2414) called render_check.main() without moving HERE and wrote a FIXTURE verdict -
    abortedAt "state-panel", renderFailures 1 - over tv/.render_verdict.json; MEASURED in the branch's own worktree
    (04:02), and every sandbox built after it carried that file. A record is never part of the bytes a law is proved on:
    the key leaves these names out (_SELF_RECORDS), so a law that read one was proved on a live value no key held. CI
    checks out none of the untracked ones and HEAD's blob of the tracked one; a sandbox now matches it.
    ⚠ CAN NOT SAY "TRACKED": with no history in the sandbox, heart2's own records still go (git never tracks them) and a
    gate run's record stays as copied - said, never silent."""
    own = {"tv/" + n for n in _SELF_RECORDS}
    recs = set(own)
    try:
        import suite_verdict as _SV
        recs |= {str(r) for r in _SV.RUN_RECORDS}
    except Exception as e:
        say("  ⚠ suite_verdict will not import (%s), so which records a gate run writes is UNKNOWN - only heart2's own "
            "were taken out of the sandbox" % type(e).__name__)
    root = os.path.normpath(dest)
    present = sorted(r for r in recs - set(keep or ())
                     if os.path.lexists(os.path.join(root, *r.split("/"))))
    if not present:
        _arm_lane_records(dest, keep, recs)
        return {}
    env = _git_free_env(GIT_OPTIONAL_LOCKS="0")
    gd = os.path.join(root, ".git")
    git = ["git", "--git-dir=" + gd, "--work-tree=" + root, "-c", "core.hooksPath=" + os.devnull]
    tracked = None
    if os.path.isdir(gd):
        try:
            r = subprocess.run(git + ["ls-tree", "-z", "--name-only", "HEAD", "--"] + present, cwd=root,
                               capture_output=True, timeout=60, env=env)
            if r.returncode == 0:
                tracked = {n for n in r.stdout.decode("utf-8", "replace").split("\0") if n}
        except (OSError, subprocess.SubprocessError):
            tracked = None
    done = {}
    for rel in present:
        p = os.path.normpath(os.path.join(root, *rel.split("/")))
        if not p.startswith(root + os.sep):
            done[rel] = "kept: it does not lie inside the sandbox"      # a record list naming `..`: never followed
            continue
        if tracked is not None and rel in tracked:
            try:
                ok = subprocess.run(git + ["checkout", "-q", "HEAD", "--", rel], cwd=root, capture_output=True,
                                    timeout=60, env=env).returncode == 0
            except (OSError, subprocess.SubprocessError):
                ok = False
            done[rel] = "HEAD's blob" if ok else "kept: its history could not restore HEAD's blob"
        elif tracked is not None or rel in own:
            try:
                os.remove(p)
                done[rel] = "removed"
            except OSError as e:
                done[rel] = "kept: it could not be removed (%s)" % type(e).__name__
        else:
            done[rel] = "kept: the sandbox holds no history to say whether git tracks it"
    kept = ["%s (%s)" % (r, w[len("kept: "):]) for r, w in sorted(done.items()) if w.startswith("kept: ")]
    if kept:
        say("  ⚠ %d live run record(s) stay in the sandbox, so a law that reads one reads a live value: %s"
            % (len(kept), "; ".join(kept)))
    _arm_lane_records(dest, keep, recs)
    return done


#: REG-2598 - {sandbox root: {record: its bytes | None (absent)} as _drop_run_records left the sandbox}
_LANE_RECORDS = {}


def _read_record(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def _arm_lane_records(dest, keep, recs):
    """REG-2598 - remember the BYTES of every run record of the sandbox at `dest` as _drop_run_records just left it,
    the records a gate keeps included (second eye: a kept record a gate rewrites is put back too)."""
    root = os.path.normpath(dest)
    snap = {}
    for r in sorted(set(recs)):                 # every record, the ones a gate keeps too
        p = os.path.normpath(os.path.join(root, *str(r).split("/")))
        if p.startswith(root + os.sep):
            snap[str(r)] = _read_record(p)
    _LANE_RECORDS[root] = snap


def _reset_lane_records(sandbox, say):
    """REG-2598 - A GATE NEVER STARTS ON A RUN RECORD THE GATE BEFORE IT WROTE. -> [records put back] | None (unarmed)

    MEASURED on the dcff7160 16-shard run: shard 16's lane ran hover-wilson, whose hover_wilson.py banks a row into
    tv/.self_arming.jsonl - a run record git tracks, and a named input of every law that reaches self_arming. Every law
    that lane proved after it (91 proofs in 12 laws) was keyed and proved over that row, so its key matched no checkout's
    bytes and the import could not serve one of them. _drop_run_records cleaned the sandbox once, when it was built; a
    lane proves many gates in it. Each gate now starts from the exact bytes the sandbox was built with - written back, or
    removed where the build left none. The baseline is never re-armed: a record that could not be put back is said and
    tried again before the next gate (second eye: re-arming a failed put-back made it the new truth)."""
    root = os.path.dirname(os.path.normpath(sandbox))
    was = _LANE_RECORDS.get(root)
    if was is None:
        return None
    moved, stuck = [], []
    for rel, data in sorted(was.items()):
        p = os.path.join(root, *rel.split("/"))
        try:
            if _read_record(p) == data:
                continue
            moved.append(rel)
            if data is None:
                os.remove(p)
            else:
                if not _inside(root, p):            # REG-2598 - a run record is put back only inside the sandbox root
                    raise OSError("outside the sandbox root")
                with open(p, "wb") as fh:
                    fh.write(data)
            if _read_record(p) != data:
                stuck.append(rel)
        except OSError:
            if rel not in moved:
                moved.append(rel)
            stuck.append(rel)
    if moved:
        say("     ↺ REG-2598 a gate before this one wrote %s in this lane's sandbox - put back as the sandbox was built, "
            "so no later law is proved or keyed over it" % ", ".join(moved))
    if stuck:
        say("     ⚠ REG-2598 %s could NOT be put back - the next law in this lane runs over what the last gate wrote"
            % ", ".join(stuck))
    return moved


def _track_sandbox(root):
    """Register a sandbox the moment it exists, and stamp it with this process as its owner."""
    _SANDBOXES.add(root)
    try:
        with open(os.path.join(root, _SANDBOX_OWNER), "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass
    _sweep_journal(os.path.dirname(root), "created", root, "new", str(os.getpid()), time.time())   # REG-2612
    return root


def _rmtree_hard(path):
    """REG-1746 — remove a tree even where a permission bit stands in the way. -> True when it is GONE.

    MEASURED on the ALT, 2026-10-02: 72 heart2 sandboxes in its TEMP since 09-29, 20,345 MB, with 25.8 GB free.
    Each held three files - the git pack (.idx/.pack/.rev, ~280 MB) - because git writes packs READ-ONLY and
    Windows refuses to unlink a read-only file ("[WinError 5] Access is denied"). rmtree(ignore_errors=True)
    swallowed that, after deleting the owner file first, so the stale sweep then read every leftover as "no
    owner" and failed on the same pack every time it tried. The Mac never saw it: POSIX unlinks a read-only file
    in a writable directory. So: a plain pass, then clear the bits on whatever is left and pass again - and the
    answer is whether the path still exists, never that the call returned. [[unknown-stays-unknown]]
    """
    shutil.rmtree(path, ignore_errors=True)
    if not os.path.exists(path):
        return True
    for dp, dns, fns in os.walk(path):
        for n in dns:
            try:
                os.chmod(os.path.join(dp, n), 0o700)
            except OSError:
                pass
        for n in fns:
            try:
                os.chmod(os.path.join(dp, n), 0o600)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)
    return not os.path.exists(path)


def _drop_sandbox(root):
    _SANDBOXES.discard(root)
    _sweep_journal(os.path.dirname(root), "dropped", root, "own-drop", str(os.getpid()), time.time())   # REG-2612
    if not _rmtree_hard(root):
        sys.stderr.write("  a sandbox could not be removed (it stays on disk until the next sweep): %s\n" % root)


def _remove_all_sandboxes():
    for root in list(_SANDBOXES):
        _drop_sandbox(root)


def _flush_on_kill():
    """#150 (REG-2943) - the push's verdict cache, flushed on the way out of a fatal signal. -> True when written.
    Only entries already store()d are written - a PROVEN in _CLEAN.pending has no green bracket yet. The cache's lock is
    tried, never waited on: the signal may have landed inside the code holding it, and a handler that blocks there
    never exits."""
    cache = getattr(_PUSH, "cache", None)
    if cache is None:
        return False
    try:
        if not cache.lock.acquire(False):
            return False
        cache.lock.release()
        return bool(cache.flush())
    except Exception:
        return False


def _on_fatal_signal(signum, frame):
    """A signal that would kill the prover removes its sandboxes first, then exits the way the signal meant to.
    #150 (REG-2943) - and first writes what the push already BANKED (stored, not yet flushed): never a PROVEN still
    waiting for a clean run, and never by waiting on a lock the interrupted code may hold."""
    _flush_on_kill()
    _remove_all_sandboxes()
    os._exit(128 + int(signum))


def install_sandbox_cleanup():
    """-> the signals now covered. Only the main thread may install a handler; anywhere else this is a no-op.
    REG-2350 - SIGINT too: a Ctrl-C raised KeyboardInterrupt in the main thread only, the lanes ran on behind it with
    their sandboxes, and the law runs the same Ctrl-C killed read as RED. Now it ends the prover like the others."""
    import signal
    done = []
    for name in ("SIGTERM", "SIGALRM", "SIGHUP", "SIGINT"):  # REG-2350 - SIGINT
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _on_fatal_signal)
            done.append(name)
        except (ValueError, OSError):
            pass
    return done


def sweep_stale_sandboxes(tmp=None, now=None):
    """Remove every heart2.* sandbox whose owner is dead, or that is older than a day whoever its owner file names.
    -> [(path, why)] removed. A live owner's sandbox is kept for a day - no proof run lives that long (the gate bounds one
    near 70 minutes), so past SANDBOX_STALE_S a "live" owner is a REUSED pid, not a prover (#231 on v3507). ⚠ This line
    said "kept, whatever its age" after that rule shipped, and the eye on v3508 read the docstring against the code."""
    tmp = tmp or tempfile.gettempdir()
    now = time.time() if now is None else now
    gone = []
    try:
        names = os.listdir(tmp)
    except OSError:
        return gone
    for n in sorted(names):
        if not n.startswith("heart2."):
            continue
        root = os.path.join(tmp, n)
        if not os.path.isdir(root) or root in _SANDBOXES:
            continue
        owner = None
        try:
            with open(os.path.join(root, _SANDBOX_OWNER)) as f:
                owner = f.read().strip()
        except OSError:
            pass
        try:
            age = now - os.path.getmtime(root)
        except OSError:
            continue
        # the #231 eye on v3507: a pid is REUSED - an owner that died without its signal handler (SIGKILL) leaves a
        # number some unrelated long-lived process may carry next, and "alive" would keep the copy forever. No proof
        # run lives a day, so past SANDBOX_STALE_S a sandbox is stale whoever its owner file names.
        if owner and _pid_alive(owner) and age < SANDBOX_STALE_S:
            continue
        if owner and age < SANDBOX_STALE_S:
            why = "its owner (pid %s) is dead" % owner
        elif age >= SANDBOX_STALE_S:
            why = "%.0f h old - no proof run lives that long%s" % (age / 3600.0, (" (owner pid %s)" % owner) if owner else "")
        else:
            continue
        _sweep_journal(tmp, "swept", root, "owner-dead" if age < SANDBOX_STALE_S else "stale-24h", owner, now)  # REG-2612
        #           ^ written BEFORE the remove, so a half-done one shows
        if _rmtree_hard(root):                  # REG-1746 — a read-only git pack kept 71 of these on the ALT
            gone.append((root, why))
    return gone


_SWEEP_JOURNAL = "heart2-sweeps.log"
_JOURNAL_CAP = 1024 * 1024          # past this the journal keeps only its last _JOURNAL_KEEP bytes
_JOURNAL_KEEP = 256 * 1024


def _write_all(fd, data):
    """os.write until every byte is down: a short write is not a whole line (review r3)."""
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        if n <= 0:
            raise OSError("short write")
        view = view[n:]


#: Windows has no flock: msvcrt locks a byte far past any journal (Windows locks are mandatory, so a locked byte a
#: reader reads would fail its read). Every writer locks the same byte, so writers take turns as they do under flock.
_JOURNAL_LOCK_AT = 0x7FFFFFF0
_JOURNAL_LOCK_WAIT_S = 30.0         # a Windows journal writer polls this long, then appends without the cap and says so


def _journal_lock(fd):
    """Exclusive writer lock on the journal -> unlock(), or None when it could not be had. flock on POSIX,
    msvcrt.locking on Windows polled with LK_NBLCK for _JOURNAL_LOCK_WAIT_S (review r4: LK_LOCK gives up after ~10 s
    and the old fallback then capped UNLOCKED, cutting under a holder). A lock not had is not a reason to lose the
    line - the caller still appends it, but never caps (a torn line fails the exact-field match and never misnames)."""
    try:
        import fcntl
    except ImportError:
        fcntl = None
    if fcntl is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            return lambda: None             # released by close
        except OSError:
            return None
    try:
        import msvcrt
    except ImportError:
        return None
    deadline = time.time() + _JOURNAL_LOCK_WAIT_S
    while True:
        try:
            os.lseek(fd, _JOURNAL_LOCK_AT, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            break
        except (OSError, ValueError):
            if time.time() >= deadline:
                return None
            time.sleep(0.05)

    def _unlock():
        try:
            os.lseek(fd, _JOURNAL_LOCK_AT, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    return _unlock


def _sweep_journal(tmp, event, root, code, owner, now):
    """REG-2612 (#71) - EVERY SANDBOX THAT IS MADE OR REMOVED IS WRITTEN DOWN WHERE THE NEXT VANISH CAN READ IT.

    #144's files vanished again on the Linux box (2026-10-23 01:11-02:21 IDT stage run, lane 4: every root .md/.html/.json
    and 13 tv files, mid-run, while a gate that touches no files was running). That box has no dirhelper, cron or
    tmpreaper, so REG-2438's macOS atime theory is not the whole cause. The deletion pattern is an rmtree's, and the
    leftover sandbox had lost its owner file - which only an rmtree of the whole sandbox removes. A sibling prover's
    sweep is one candidate; nothing recorded it. This journal does.

    One line per event: `<epoch s>\t<created|swept|dropped>\tpid=<n>\t<heart2.* basename>\towner=<n|->\t<code>`. Only
    integers, the basename and a fixed code: no repo text, and nothing an owner file holds is copied (the vanish note
    rides the gate tail heart2 parses). Mode 0600; every write placed by lseek under an exclusive writer lock (flock,
    or msvcrt on Windows); capped. A write that fails is SAID on stderr - a silent one is what would make a real
    sweep read as "no line"."""
    own = str(owner or "").strip()
    line = "%d\t%s\tpid=%d\t%s\towner=%s\t%s\n" % (
        int(now), event, os.getpid(), os.path.basename(root), own if own.isdigit() else ("?" if own else "-"), code)
    path = os.path.join(tmp, _SWEEP_JOURNAL)
    try:
        # review r3: NO O_APPEND. The cap must write at offset 0, and an O_APPEND fd cannot; every write is placed by
        # an explicit lseek under the lock instead, so no OS's idea of append decides where a line lands.
        # v3886 (#107, windows-latest: "the cap left a torn line") - O_BINARY: Windows opens a bare os.open fd in TEXT
        # mode, so every "\n" written became "\r\n" on disk while the cap below counts and cuts in bytes it read back
        # translated - the cut landed inside a line. Binary on every OS (O_BINARY is 0 / absent off Windows).
        fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o600)
        try:
            unlock = _journal_lock(fd)
            held = unlock is not None
            if not held:
                # review r4: no lock, no cap - a cut made beside a holder's cap could drop the line it just wrote
                sys.stderr.write("  #71 the sandbox journal lock was not had: line appended, cap skipped\n")
                unlock = lambda: None
            try:
                os.lseek(fd, 0, os.SEEK_END)
                _write_all(fd, line.encode("ascii", "replace"))
                if held and os.fstat(fd).st_size > _JOURNAL_CAP:
                    # capped IN PLACE, under the same lock (review r2): the kept tail is written at offset 0 FIRST
                    # and only then is the file cut to it (review r3), so a reader never sees it empty - at worst
                    # the kept lines followed by older ones, which are still true lines.
                    os.lseek(fd, -_JOURNAL_KEEP, os.SEEK_END)
                    keep = b""
                    while len(keep) < _JOURNAL_KEEP:
                        chunk = os.read(fd, _JOURNAL_KEEP - len(keep))
                        if not chunk:
                            break
                        keep += chunk
                    keep = keep[keep.find(b"\n") + 1:]
                    os.lseek(fd, 0, os.SEEK_SET)
                    _write_all(fd, keep)
                    os.ftruncate(fd, len(keep))
            finally:
                unlock()
        finally:
            os.close(fd)
    except Exception as e:
        try:
            sys.stderr.write("  #71 the sandbox journal was not written (%s %s %s)\n"
                             % (event, os.path.basename(root), type(e).__name__))
        except Exception:
            pass


def _journal_lines_for(tmp, name):
    """The journal's lines naming exactly this sandbox, parsed -> [(epoch, event, pid, owner, code)]. Reads only the
    last _JOURNAL_KEEP bytes, decoded with errors replaced; a line that does not parse is skipped."""
    path = os.path.join(tmp, _SWEEP_JOURNAL)
    with open(path, "rb") as fh:
        try:
            fh.seek(-_JOURNAL_KEEP, os.SEEK_END)
        except OSError:
            fh.seek(0)
        text = fh.read().decode("utf-8", "replace")
    out = []
    for ln in text.splitlines():
        f = ln.split("\t")
        if len(f) != 6 or f[3] != name or not f[0].isdigit() or not f[2].startswith("pid=") \
                or not f[2][4:].isdigit() or not f[4].startswith("owner="):
            continue
        out.append((int(f[0]), f[1], int(f[2][4:]), f[4][6:], f[5]))
    return out


_JOURNAL_SAYS = {"owner-dead": "its owner pid was dead", "stale-24h": "over a day old", "own-drop": "its own run's end",
                 "new": "made"}


def _vanish_witness(sb_root, now=None):
    """REG-2612 (#71) - what the sandbox and the journal say at the moment a vanish is seen. -> str, never raises.

    Whether the owner file and the sandbox root survive, when and by which pid the sandbox was CREATED (from the journal
    - the root's mtime moves whenever a direct child is unlinked, so it cannot date the sandbox), and every removal the
    journal names for exactly this sandbox. Owner gone with no removal line is said as that: an unlink inside the
    sandbox, an outside rmtree, or a sweep whose line failed (said on stderr then) - not guessed."""
    try:
        now = time.time() if now is None else now
        base = os.path.dirname(sb_root)
        name = os.path.basename(base)
        parts = ["owner file %s" % ("present" if os.path.isfile(os.path.join(base, _SANDBOX_OWNER)) else "GONE"),
                 "sandbox root %s" % ("present" if os.path.isdir(base) else "GONE")]
        try:
            rows = _journal_lines_for(os.path.dirname(base), name)
        except OSError:
            rows = []
        made = [r for r in rows if r[1] == "created"]
        parts.append(("created %ds ago by pid %d" % (max(0, int(now) - made[-1][0]), made[-1][2])) if made
                     else "no created line")
        rm = ["%s by pid %d (%s, owner %s)" % (r[1], r[2], _JOURNAL_SAYS.get(r[4], "?"), r[3] if r[3].isdigit() else "-")
              for r in rows if r[1] in ("swept", "dropped")]
        parts.append(("removal: " + " | ".join(rm[-3:])) if rm else "no sweep journal line names it")
        return "; ".join(parts)
    except Exception as e:
        return "witness unreadable (%s)" % type(e).__name__


def make_sandbox(say=print):
    """A throwaway copy of the repo via safe_copy.py. -> (tv_path, root) | (None, None)

    ⚠⚠ TWO OF MY OWN MISTAKES LIVE IN THIS FUNCTION'S HISTORY, and both produced a confident
    wrong answer rather than an error:

      1. `safe_copy.copy()` REFUSES when the destination already exists — "Remove it yourself,
         deliberately" — and `tempfile.mkdtemp()` CREATES the directory. So it was handed a path
         it was designed to reject, every time.
      2. Its RETURN CODE was ignored. It answered 2, wrote nothing, and the code sailed on to
         report five gates UNPROVABLE with the reason "control_app.py is not in the sandbox" —
         true, and about a sandbox that did not exist. A refusal read as success.
         [[exit-status-of-the-block]]

    The protocol is what saved it: because a clean run is required BEFORE any tamper, an empty
    sandbox came out as UNPROVABLE and never as BLIND or PROVEN. A missing file could not be
    mistaken for a passing gate. That ordering is the whole reason the verdicts are trustworthy.
    """
    root = _track_sandbox(tempfile.mkdtemp(prefix="heart2."))
    dest = os.path.join(root, "repo")          # must NOT exist — safe_copy refuses if it does
    try:
        import safe_copy
    except Exception as e:
        say("  safe_copy will not import (%s) — refusing to tamper anywhere else" % e)
        _drop_sandbox(root)
        return None, None
    _said = []
    try:
        rc = safe_copy.copy(REPO, dest, False, lambda *a, **k: _said.append(str(a[0]) if a else ""))
    except Exception as e:
        say("  the sandbox could not be built: %s" % type(e).__name__)
        _drop_sandbox(root)
        return None, None
    if rc not in (0, None):
        # REG-1845 — AND SAY WHY. The refusal's own sentence was handed to a no-op, so his log said "exit 1"
        # 125 times while the reason (420.4 MB over the 400 MB ceiling) was never written anywhere.
        _why = next((t for t in reversed(_said) if t.startswith("REFUSED")), "") or "no reason was given"
        say("  safe_copy REFUSED the sandbox (exit %s): %s — nothing was copied, so nothing can be "
            "proven. That is UNKNOWN, not clean." % (rc, _why[:240]))
        _drop_sandbox(root)
        return None, None
    # ⚠⚠ v2821 — SAFE_COPY COPIES `tv/` ONLY, AND 59 OF 259 GATES READ `bible.html`.
    # That file lives in the repo ROOT, so every law about the bible came back UNPROVABLE with
    # "bible.html is not in the sandbox" — 23% of the suite structurally unable to prove itself,
    # for want of one 6.1 MB file. Measured, not estimated: 59 gates name it.
    #
    # ⚠ ONE FILE, BY NAME. NEVER `cp -R` of the repo or of tv/ — tv/ holds ~5.8 GB of footage and
    # copying it caused an ENOSPC once already. safe_copy exists precisely to avoid that, and this
    # adds a single named file beside its output rather than widening what it copies.
    # v2882 — visual_lock_invariant.py joins bible.html here: it is the one GATE whose file lives
    # in the repo root, and without it in the sandbox `visual-lock` cannot be proven.
    # ⚠⚠ v2888 — BRING ACROSS THE DATA A GATE DECLARED, AND NOTHING ELSE.
    # `cp -c` is an APFS CLONE: no bytes are copied and no disk is spent, and a write inside the
    # sandbox lands on the copy rather than on his real footage — which matters here because these
    # ARE his screenshots. Only paths a gate names in PROOF_NEEDS come over; there is no glob and
    # no recursion into tv/ at large, because that is the ENOSPC that safe_copy exists to prevent.
    _needs, _unreadable = set(), []
    for _gn, _fn in gate_files(say=lambda *a, **k: None):
        _got = proof_needs_in(_fn)
        if _got is None:
            _unreadable.append(_gn)     # NOT "declares nothing" — nobody could tell
            continue
        _needs.update(_got)
    if _unreadable:
        say("  ⚠ %d gate file(s) would not parse, so whether they declare PROOF_NEEDS is UNKNOWN, "
            "not none: %s" % (len(_unreadable), ", ".join(_unreadable[:6])))
    for _need in sorted(_needs):
        # ⚠ v2888 — A NEED MAY REACH ABOVE tv/ ("../.git"), BECAUSE NOT EVERY SUBJECT LIVES IN tv/.
        # test_tasks_ships_are_recorded reads GIT HISTORY, and a sandbox is a copy with no .git, so
        # it failed with "git named 0 shipped versions on a FULL clone" — a sentence that asserts
        # it is NOT a venue problem while standing in exactly that venue. Both sides are normalised
        # and checked for containment, so a need can never escape the repo or the sandbox.
        _s = os.path.normpath(os.path.join(REPO, "tv", _need))
        _inside = os.path.normpath(REPO) + os.sep
        if not (_s + os.sep).startswith(_inside):
            say("  PROOF_NEEDS %r points outside the repo — refusing to bring it across" % _need)
            continue
        if not os.path.exists(_s):
            say("  a gate declares PROOF_NEEDS %r and it is not on this machine — that gate stays "
                "UNPROVABLE here, which is the honest verdict" % _need)
            continue
        if os.path.isfile(_s) and os.path.basename(_s) == ".git":
            # ⚠ A `.git` FILE IS A POINTER INTO ANOTHER CHECKOUT, NOT A HISTORY. In a linked worktree `.git` is one
            # line - `gitdir: <the main checkout's .git/worktrees/...>` - and cloned into the sandbox it makes every
            # git command a law runs there read, and could make it WRITE, that real worktree's index and HEAD (found
            # by the second eye through the #42 P3 key, which listed `.git` among a law's inputs: a stable string,
            # but a door). safe_copy already drops a file named .git; this is the one copier that brought it. A
            # sandbox holds no door to the real repo: the need stays out, said, and the gate that declared it reads
            # UNPROVABLE here. Where .git is a directory (his main checkout, where the push runs) the clone is a
            # full private copy, exactly as before. [[feedback-fixtures-never-touch-live-data]]
            # ⚠⚠ REG-2364 — AND LEFT OUT, IT LEFT A WORKTREE'S SANDBOX WITH NO HISTORY AT ALL. Nobody saw it, because
            # the hook leaked GIT_DIR: every git call a law made in here answered from - and could write - the real
            # worktree through it. Pushes run from worktrees now and the hook unsets GIT_DIR (REG-2360), and MEASURED
            # on that branch: test_control's relaunch case errored on `git rev-parse HEAD` (a red clean run refuses the
            # push) and the version-stamp law's red-proof [7] went BLIND (its only catcher skips without history). So
            # the pointer is still never copied; the sandbox gets a PRIVATE clone of that checkout's history instead
            # (_share_history: HEAD is the worktree's HEAD, the objects borrowed read-only, the push shut). Only when
            # no clone can be made does the gate that declared it stay UNPROVABLE here, said.
            _dg = os.path.normpath(os.path.join(dest, "tv", _need))
            if ((_dg + os.sep).startswith(os.path.normpath(dest) + os.sep)
                    and _share_history(os.path.dirname(_s), _dg, say)):
                continue
            say("  PROOF_NEEDS %r is a worktree POINTER (a file naming another checkout's git dir), not a history "
                "- not brought across, so the gate that declared it stays UNPROVABLE in this sandbox" % _need)
            continue
        _d = os.path.normpath(os.path.join(dest, "tv", _need))
        if not (_d + os.sep).startswith(os.path.normpath(dest) + os.sep):
            say("  PROOF_NEEDS %r would land outside the sandbox — refused" % _need)
            continue
        try:
            os.makedirs(os.path.dirname(_d), exist_ok=True)
            _bring_across(_s, _d, _need, say)
        except Exception as _e:
            say("  PROOF_NEEDS %r could not be brought across: %s" % (_need, type(_e).__name__))
    for _root_file in ("bible.html", "visual_lock_invariant.py"):
        _srcf = os.path.join(REPO, _root_file)
        if os.path.isfile(_srcf):
            try:
                shutil.copy2(_srcf, os.path.join(dest, _root_file))
            except Exception as _e:
                # not fatal: the bible-reading gates will simply report UNPROVABLE as before,
                # which is the honest outcome. It must never silently look like a pass.
                say("  could not place %s in the sandbox (%s) — gates that read it stay UNPROVABLE"
                    % (_root_file, type(_e).__name__))
    # REG-2365 — A SANDBOX NEVER CARRIES A LIVE RUN RECORD (the census, the render verdict, the proof ledger): removed, or
    # HEAD's blob where git tracks it - after the history above, which restores it. See _drop_run_records.
    try:
        _drop_run_records(dest, {os.path.normpath(os.path.join("tv", _n)).replace(os.sep, "/") for _n in _needs}, say)
    except Exception as _e:
        say("  ⚠ the run records could not be taken out of the sandbox (%s) - a law that reads one reads a live value"
            % type(_e).__name__)
    tv = os.path.join(dest, "tv")
    if not os.path.isfile(os.path.join(tv, "control_app.py")):
        say("  the sandbox is missing control_app.py — refusing to report verdicts about it")
        _drop_sandbox(root)
        return None, None
    return tv, root


def _skipped_every_law(tail):
    """REG-2354 — did this run skip EVERY law it ran? -> bool. The two numbers blind_reason's "ALL n law(s) SKIPPED" line
    is printed from; a run that did not say how many it ran answers False here and is judged exactly as before."""
    _sk = re.search(r"skipped=(\d+)", tail or "")
    _rn = re.search(r"Ran (\d+) test", tail or "")
    return bool(_sk and _rn and int(_rn.group(1)) > 0 and int(_sk.group(1)) >= int(_rn.group(1)))


def _skip_count(tail, which):
    """REG-2359 — what one run's own tail says it skipped: 'clean run: 4 of 4 skipped'. -> str ('?' for a number it
    did not print)"""
    _sk = re.search(r"skipped=(\d+)", tail or "")
    _rn = re.search(r"Ran (\d+) test", tail or "")
    return "%s run: %s of %s skipped" % (which, _sk.group(1) if _sk else "?", _rn.group(1) if _rn else "?")


#: REG-2359 — a skip reason that names node ("node is absent", "no node on PATH", "Node.js ..."; never node_modules)
_NAMES_NODE = re.compile(r"\bnode(?:\.?js)?\b", re.I)


def _case_key(case):
    """REG-2359 — unittest's case id (`__main__.Class.test_x`, or `pkg.mod.Class.test_x`) as posix_only_cases() names a
    case (`Class.test_x`). -> str"""
    parts = str(case or "").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else str(case or "")


def _skipped_for_want(tail, skips, off_posix=frozenset(), posix_gone=False):
    """REG-2359 — did EVERY case this run skipped skip for want of something this PC lacks? -> (node skips, POSIX skips)
    when it did, None when it did not

    The skip watch saw exactly as many skips as the run reported (`skipped=N` in its tail), at least one reason names
    node, and every other skip is a case that runs only on POSIX (posix_only_cases, read from the gate's source) on a
    PC without POSIX. Anything else is None and the proof is judged exactly as before: no watch (None), a skip the watch
    could not see (a result class that never reaches TestResult.addSkip), a count that does not match, or ONE skip for
    any other reason - a law that skips for want of his D2R install is not excused by node's absence."""
    if not isinstance(skips, list) or not skips:
        return None
    _sk = re.search(r"skipped=(\d+)", tail or "")
    if not _sk or int(_sk.group(1)) != len(skips):  # SKIPS-ALL-SEEN
        return None
    node = [s for s in skips if _NAMES_NODE.search(str(s[1]))]
    posix = [s for s in skips if s not in node and posix_gone and _case_key(s[0]) in off_posix]  # SKIP-OFF-POSIX-CASE
    if not node or len(node) + len(posix) != len(skips):  # SKIPS-ALL-WANTED
        return None
    return node, posix


#: REG-2354 — how a gate reaches for node: measured, these three spellings cover all 54 node gates Dean's PC filed BLIND.
_GATE_NAMES_NODE = re.compile(r"""shutil\.which\(\s*["']node["']\s*\)|["']node["']|\bNODE\b""")


def _gate_reaches_for_node(sandbox, filename):
    """REG-2354 — does this gate's own source reach for node? -> bool. The sandbox copy first, then the repo's; a file
    that will not read answers False, so an unreadable gate is judged exactly as before and never excused."""
    for _p in (os.path.join(sandbox, filename), os.path.join(REPO, "tv", filename)):
        try:
            with io.open(_p, encoding="utf-8", errors="replace") as fh:
                return bool(_GATE_NAMES_NODE.search(fh.read()))
        except Exception:
            continue
    return False


# ══ REG-2357 — A LAW WHOSE CASES ALL SKIP OFF POSIX SAYS SO ON EVERY PROOF, OR WINDOWS FILES IT BLIND ═══════════════════
# test_a_killed_run_is_never_a_red holds its 17 cases in three classes, each `skipUnless(_POSIX)`, and declared no need on
# any of its 26 red-proofs. On Windows every case skips in the clean run AND the tampered one, so all 26 file BLIND there,
# and one BLIND shuts every lock on that PC (REG-1677). Such a law can be judged only where POSIX is, so each of its proofs
# must declare it (`"needs": "posix-signals"`, "posix" or "macos"); REG-1686 then files it ELSEWHERE on Windows. A proof
# that does not is INVALID here, on the PC that CAN judge it, before it ever reaches a Windows census. A proof whose
# CATCHING cases (the ones that went red) all skip off POSIX, in a law with other cases, is said, never refused: that
# shape is known only from a run, and a refusal there would land on proofs this PC has already banked.
# The skip decorators are read from the gate's source WITHOUT importing it. Each condition is evaluated twice, as Windows
# and as macOS would compute it: os.name, sys.platform, hasattr(signal | os, ...), module-level names, and/or/not,
# comparisons, str.startswith. A case is off-POSIX only when it skips on the first and not on the second. A condition this
# reader cannot evaluate counts as "it may run there", so no proof is refused on a guess. [[unknown-stays-unknown]]
_OFF_POSIX_NEEDS = frozenset(("posix", "posix-signals", "macos"))
_WIN_SIGNALS = frozenset(("SIGABRT", "SIGBREAK", "SIGFPE", "SIGILL", "SIGINT", "SIGSEGV", "SIGTERM", "CTRL_C_EVENT",
                          "CTRL_BREAK_EVENT"))
_POSIX_ONLY_OS = frozenset(("fork", "forkpty", "killpg", "getpgid", "getpgrp", "setpgid", "setpgrp", "setsid", "getuid",
                            "geteuid", "getgid", "getegid", "WNOHANG", "mkfifo", "statvfs", "getloadavg"))
_WIN_ONLY_OS = frozenset(("startfile", "add_dll_directory", "O_BINARY"))
_UNKNOWN_V = object()
_POSIX_ONLY_MEMO = {}


def _as_platform(node, plat, names, depth=0):
    """REG-2357 — a skip condition's value as `plat` ("win32" | "darwin") would compute it. -> value | _UNKNOWN_V"""
    unk = _UNKNOWN_V
    if node is None or depth > 8:
        return unk
    win = plat == "win32"
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        vals = [_as_platform(e, plat, names, depth + 1) for e in node.elts]
        return unk if any(v is unk for v in vals) else tuple(vals)
    if isinstance(node, ast.Name):
        return _as_platform(names[node.id], plat, names, depth + 1) if node.id in names else unk
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if (node.value.id, node.attr) == ("os", "name"):
            return "nt" if win else "posix"
        if (node.value.id, node.attr) == ("sys", "platform"):
            return plat
        return unk
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        v = _as_platform(node.operand, plat, names, depth + 1)
        return unk if v is unk else (not v)
    if isinstance(node, ast.BoolOp):
        vals = [_as_platform(v, plat, names, depth + 1) for v in node.values]
        conj = isinstance(node.op, ast.And)
        if any(v is not unk and bool(v) != conj for v in vals):
            return not conj                     # one known falsy operand decides an `and`, one truthy an `or`
        return unk if any(v is unk for v in vals) else conj
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        a = _as_platform(node.left, plat, names, depth + 1)
        b = _as_platform(node.comparators[0], plat, names, depth + 1)
        if a is unk or b is unk:
            return unk
        ops = {ast.Eq: lambda x, y: x == y, ast.NotEq: lambda x, y: x != y, ast.In: lambda x, y: x in y,
               ast.NotIn: lambda x, y: x not in y, ast.Is: lambda x, y: x is y, ast.IsNot: lambda x, y: x is not y}
        fn = ops.get(type(node.ops[0]))
        try:
            return fn(a, b) if fn else unk
        except TypeError:
            return unk
    if isinstance(node, ast.Call) and not node.keywords:
        f = node.func
        if isinstance(f, ast.Name) and f.id == "hasattr" and len(node.args) == 2 \
                and isinstance(node.args[0], ast.Name) and isinstance(node.args[1], ast.Constant):
            mod, attr = node.args[0].id, str(node.args[1].value)
            if mod == "signal" and attr.startswith(("SIG", "CTRL_")):
                return (attr in _WIN_SIGNALS) if win else (attr not in ("SIGBREAK", "CTRL_C_EVENT", "CTRL_BREAK_EVENT"))
            if mod == "os" and attr in _POSIX_ONLY_OS:
                return not win
            if mod == "os" and attr in _WIN_ONLY_OS:
                return win
            return unk
        if isinstance(f, ast.Attribute) and f.attr == "startswith" and len(node.args) == 1:
            s = _as_platform(f.value, plat, names, depth + 1)
            pre = _as_platform(node.args[0], plat, names, depth + 1)
            if isinstance(s, str) and (isinstance(pre, str) or (isinstance(pre, tuple) and pre
                                                                and all(isinstance(x, str) for x in pre))):
                return s.startswith(pre)
        return unk
    return unk


def _skips_under(deco, plat, names, depth=0):
    """REG-2357 — does this decorator skip its case under `plat`? -> True | False (not a skip, or it runs) | _UNKNOWN_V"""
    if isinstance(deco, ast.Name) and deco.id in names and depth < 3:
        return _skips_under(names[deco.id], plat, names, depth + 1)     # `posix_only = unittest.skipUnless(...)`
    if not isinstance(deco, ast.Call):
        return False
    fn = deco.func
    which = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
    if which == "skip":
        return True
    if which not in ("skipIf", "skipUnless") or not deco.args:
        return False
    v = _as_platform(deco.args[0], plat, names)
    if v is _UNKNOWN_V:
        return _UNKNOWN_V
    return bool(v) if which == "skipIf" else (not v)


def posix_only_cases(src):
    """REG-2357 — the test cases of a gate's source that skip on Windows and not on macOS, read without importing it.
    -> (off-POSIX case ids, every case id), sets of "Class.test_x" | None when the source will not parse"""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return None
    names = dict((st.targets[0].id, st.value) for st in tree.body
                 if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name))
    off, every = set(), set()
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for m in cls.body:
            if not (isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test")):
                continue
            cid = "%s.%s" % (cls.name, m.name)
            every.add(cid)
            decos = list(cls.decorator_list) + list(m.decorator_list)
            if any(_skips_under(d, "win32", names) is True for d in decos) \
                    and not any(_skips_under(d, "darwin", names) is True for d in decos):  # POSIX-ONLY-CASE
                off.add(cid)
    return off, every


def _posix_only_of(sandbox, filename):
    """REG-2357 — posix_only_cases() of this gate's file: the sandbox copy first, then the repo's. Parsed once per
    content (test_control.py is 2.7 MB). -> (off, every) | None (it will not read or parse: nothing is refused on it).
    Never raises: it is asked inside _prove_one, where a raise is recorded BLIND, and one BLIND shuts every lock."""
    for _p in (os.path.join(sandbox, filename), os.path.join(REPO, "tv", filename)):
        try:
            with io.open(_p, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        key = hashlib.sha1(src.encode("utf-8", "replace")).hexdigest()
        if key not in _POSIX_ONLY_MEMO:
            try:
                _POSIX_ONLY_MEMO[key] = posix_only_cases(src)
            except Exception:  # POSIX-READER-NEVER-RAISES: a source too deep to parse refuses and excuses nothing
                _POSIX_ONLY_MEMO[key] = None
        return _POSIX_ONLY_MEMO[key]
    return None


def _say_posix_only_catch(sandbox, filename, label, need, ids, say):
    """REG-2357 — said (never a verdict) when every case that caught a PROVEN proof skips off POSIX and the proof declares
    no need Windows lacks: there it can never be judged, and it files BLIND. -> the ids said | []

    Round 4: and KEPT in the push record (REG-2353) - hooks/pre-push deletes its prove log on a pass, so a line alone
    reached nobody and the proof shipped to every Windows census. The record counts it in its summary line too."""
    try:
        if not ids or str(need or "") in _OFF_POSIX_NEEDS:
            return []
        got = _posix_only_of(sandbox, filename)
        ids = sorted(set(str(i) for i in ids))
        if not got or not all(i in got[0] for i in ids):  # POSIX-ONLY-CATCH
            return []
        say("     %-52s   ↳ REG-2357: every case that caught it skips off POSIX (%s), so on Windows it is never judged "
            "and files BLIND (one BLIND shuts every lock on that PC) - declare \"needs\": \"posix\" (or "
            "\"posix-signals\" / \"macos\")" % (label, ", ".join(ids[:4]) + (" +%d" % (len(ids) - 4) if len(ids) > 4
                                                                            else "")))
        _mark(posixOnly=ids[:8])  # POSIX-ONLY-RECORDED - the push record keeps it: the hook deletes this log on a pass
        return ids
    except Exception:
        return []                       # a check that cannot be made says nothing; the verdict above stands


def blind_reason(why, matches, tail, widths=None):
    """The sentence a BLIND verdict prints. -> str

    #42 — `widths` is the restriction a push-time proof DECLARED (None everywhere else). Under it a width law skips every
    case measured at other viewports BY DESIGN, so its `skipped=N` is the declaration's doing, never the law opting out:
    those skips are named as the restriction's, and the work they point at is the declaration, not a skipTest. Without
    it every sentence below reads exactly as it did. Found by the adversarial review of #42. [[unknown-stays-unknown]]

    ⚠⚠ v2866 — A SKIP IS NOT A PASS, AND THE BLIND LINE COULD NOT TELL THEM APART.
    `test_the_lock_derives_from_the_heart[1]` came back BLIND and shipped that way in v2865's own
    census. The cause was not a weak law: the law called `self.skipTest()` because `.heart2.json` is
    gitignored and therefore absent from every sandbox, so the tampered run printed
    `OK (skipped=5)` — green, because nothing ran. "stayed GREEN through its own defeat" is exactly
    wrong about that: it never reached its own defeat.

    The two cases need different work — a real BLIND needs a stronger law, a skipped one needs the
    law to stop opting out — and the line that reports them said the same thing about both. It cost
    a shipped `blind: 1` and a deduction that the tail had been carrying the answer all along.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    _base = ("stayed GREEN through its own defeat (%d match(es)): %s" % (matches, str(why)[:70]))
    _sk = re.search(r"skipped=(\d+)", tail or "")
    _rn = re.search(r"Ran (\d+) test", tail or "")
    n_skipped = int(_sk.group(1)) if _sk else 0
    if not n_skipped:
        # REG-3306 (v3875's GitHub round) - A SCRIPT GATE'S BLIND KEPT NOTHING OF WHAT IT SAW. crest_loudness[0] came back
        # BLIND on a Linux shard and PROVEN on this Mac; the tamper paints the crest solid red, and the line kept only the
        # proof's why, never the law's own verdict line under the tamper ("the crest is #N, behind X"), which is the one
        # fact that says what out-shouted a red crest there. A unittest tail ("Ran N tests | OK") says nothing more; a
        # script gate's last line is its finding, so it is quoted.
        _t = str(tail or "").strip()
        if _t and _rn is None and not re.match(r"(OK|FAILED)\b", _t):
            return _base + "  - under the tamper the law said: " + _t[:200]
        return _base
    if widths:
        import law_widths as _LW
        _at = _LW.label(widths)
        _of = int(_rn.group(1)) if _rn else None
        if _of is not None and _of <= n_skipped:
            return (_base + "  ⚠ ALL %d law(s) SKIPPED under the proof's DECLARED restriction to %s: no case of this law "
                            "measures there, so the declaration measured nothing - re-measure where the defect shows "
                            "(the skips are the restriction's, not the law opting out)." % (_of, _at))
        return (_base + "  (%d%s law(s) SKIPPED under the proof's DECLARED restriction to %s - cases measured at other "
                        "viewports skip there by design, not the law opting out; the ones that ran at %s stayed green.)"
                % (n_skipped, (" of %d" % _of) if _of is not None else "", _at, _at))
    if _rn is None:
        return (_base + "  ⚠ %d law(s) SKIPPED and the run did not say how many it ran (%s), so "
                        "whether the tamper was judged AT ALL is UNKNOWN."
                % (n_skipped, (tail or "").strip()[:60]))
    n_ran = int(_rn.group(1))
    if n_skipped >= n_ran:
        return (_base + "  ⚠ ALL %d law(s) SKIPPED in the sandbox — the tamper was never judged. "
                        "Fix the SKIP; the law itself has not been tested." % n_ran)
    return (_base + "  ⚠ %d of %d law(s) SKIPPED, but the other %d DID run and stayed green — so "
                    "the law IS weak, and separately some laws opted out. Both jobs, not one."
            % (n_skipped, n_ran, n_ran - n_skipped))


_LANE_LOCAL = threading.local()


def _stamp_lane_ports(env, lane):
    """#144 — write this prove lane's port base into the gate's environment."""
    import lane_ports as _lp
    return _lp.stamp(env, lane)


_VANISHED = []     # REG-1876 - (gate, file, lane) for every sandbox file seen gone after a run; read by vanished()


def vanished():
    """Every tracked sandbox file that was found MISSING after a gate ran, and restored. -> [(gate, file, lane)]"""
    return list(_VANISHED)


def _tv_files(sandbox_tv):
    """The sandbox files a vanishing is watched for, as paths relative to the sandbox REPO. -> set

    REG-1919 - tv/*.py alone was too narrow: v3601's push #2 was refused when test_control[2] read ALREADY RED
    untampered on TestV2395...test_the_skill_parses_and_would_actually_load - .claude/skills/human-eyes-harness/SKILL.md
    was gone from that lane's sandbox, present in a fresh one built minutes later, and the instrument (which only
    listed tv/*.py) named nothing. The project skills and the repo-root files laws read are watched too."""
    out = set()
    try:
        out |= set("tv/" + n for n in os.listdir(sandbox_tv) if n.endswith(".py"))
    except OSError:
        pass
    root = os.path.dirname(sandbox_tv)
    try:
        sk = os.path.join(root, ".claude", "skills")
        for d in os.listdir(sk):
            if os.path.isfile(os.path.join(sk, d, "SKILL.md")):
                out.add(".claude/skills/%s/SKILL.md" % d)
    except OSError:
        pass
    try:
        for n in os.listdir(root):
            if n.endswith((".md", ".html", ".json")) and os.path.isfile(os.path.join(root, n)):
                out.add(n)
    except OSError:
        pass
    return out


# REG-2631 - AN ALL-HIT PROVE RE-READ EVERY INPUT OF EVERY PROOF. MEASURED on the box, 19 gates / 226 proofs all served
# from the cache, 0 clean runs: 266 s wall, 563,770 _sha_file reads (~1,250 inputs x 452 keys: the wave's peek and the
# main pass's lookup each key every proof), every read under the cache's one lock, so four lanes hashed one at a time.
# v3792's hook on his Mac: 303 of 303 hits, 2m39 proving. The digest of a file cannot change while nothing writes it,
# and in the prover only _prove_one writes a sandbox (its tamper and restore, and the law it runs). So the keyer's digests
# are served within a QUIET STRETCH: keyed on (path, size, mtime_ns, ctime_ns, inode, generation), and _prove_one bumps
# the generation on entry and on exit. _sha_file itself still always reads (a same-size rewrite with a frozen mtime).
_QUIET = {"gen": 0}
_QUIET_LOCK = threading.Lock()


def _quiet_bump():
    with _QUIET_LOCK:
        _QUIET["gen"] += 1


def _quiet_stretch(fn):
    """REG-2631 - `fn` writes a sandbox or runs a law: the quiet stretch ends on its entry and on its exit, so a digest the
    keyer took before it is never served after it."""
    import functools

    @functools.wraps(fn)
    def run(*a, **k):
        _quiet_bump()
        try:
            return fn(*a, **k)
        finally:
            _quiet_bump()
    return run


@_quiet_stretch                         # REG-2631 - a law run (in or outside _prove_one) ends the quiet stretch
def _run_gate(sandbox_tv, filename, timeout=180, extra=(), script=None, widths=None):
    """REG-1876 (#144) - a tracked file once vanished from a lane's sandbox mid-run ("No module named ..." read as a law
    failure) and no writer was ever caught. Until one is, every run is bracketed by a census of the sandbox's tv/*.py: a
    file present before and gone after is NAMED (gate, file, lane - see vanished()), restored from the real tree, and a
    run that FAILED over it is run once more, so a missing module is never graded as the law's defect. -> (passed, tail)"""
    before = _tv_files(sandbox_tv)
    res = _run_gate_once(sandbox_tv, filename, timeout, extra, script, widths)
    gone = sorted(before - _tv_files(sandbox_tv))
    if not gone:
        return res
    restored = []
    _sb_root = os.path.dirname(sandbox_tv)
    _witness = _vanish_witness(_sb_root)     # REG-2612 (#71) - read BEFORE the restore touches it; never raises
    for n in gone:
        src = os.path.join(REPO, n)          # REG-1919 - n is relative to the repo now (tv/x.py, .claude/skills/...)
        try:
            dst = os.path.join(_sb_root, n)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            restored.append(n)
        except OSError:
            pass
        _VANISHED.append((filename, n, getattr(_LANE_LOCAL, "n", None)))
    note = " [#144: %s vanished from this sandbox during the run - %s]" % (
        ", ".join(gone), "restored from the real tree" if len(restored) == len(gone) else "NOT all restorable")
    note = note[:-1] + " - " + _witness + "]"
    sys.stderr.write("  #144 a tracked file vanished from a lane sandbox: %s (running %s, lane %s) [%s]\n"
                     % (", ".join(gone), filename, getattr(_LANE_LOCAL, "n", None), _witness))
    if res[0] is True or len(restored) != len(gone):
        return res[0], str(res[1]) + note
    again = _run_gate_once(sandbox_tv, filename, timeout, extra, script, widths)
    return again[0], str(again[1]) + note + " (re-run once)"


# ══ REG-2640 (#42 P3-fine) — A NAMED FILE THE LAW NEVER OPENED IS NOT ONE OF ITS INPUTS ══════════════════════════════
# MEASURED 2026-10-24 on v3796 r6 (control_ui.html +8 lines of CSS, render_check.py +5): the P3 key moved for 5,012 of
# 6,327 proofs and only 856 were reusable, so the Mac pre-prove re-proved from nothing for 40+ minutes. 4,411 of the
# 5,012 moved ONLY through tv/control_ui.html, and 3,474 of those laws never name that file themselves: it joins their
# key because SOME module of their import closure (heart2, run_gates, control_app...) spells "control_ui.html" in a
# string. The key was sound and far too wide: a byte of a file the law never reads cannot change its verdict.
# So a push-time law run is TRACED. A sitecustomize on PYTHONPATH (the source below; this file's own bytes, so the
# prover's hash covers it) installs a CPython audit hook - which nothing in the process can remove - before the law's
# first line, and logs the basename (and real basename) of every file the run OPENS (open, io.open_code, os.open,
# sqlite3) or STATS (os.stat / lstat / access / readlink, so exists() and getsize() count as a read), in the law and in
# every python child that inherits the hook. After a PROVEN, a NAMED DATA FILE (not .py, not the tampered target, not a
# PROOF_NEEDS, not the prover) whose basename no traced run of that law opened or stat'd in this process is keyed by
# NAME only ("unread"), and the PROVEN is banked under that key (v2). Lookup tries the byte-for-byte v1 key first, then
# each recorded unread-set for the same proof.
# ⚠ WHY IT IS SOUND (the build-system argument, under the floor v1 already states: a law is a function of its bytes):
#   the v2 key still digests the NAME of every input and the BYTES of every input the runs opened. A run over those
#   same bytes takes the same path, so it opens the same files - never one of the unread ones - and reaches the same
#   verdict. Anything that would break that is a run the trace could not see, and then NOTHING is dropped:
#   · a child that is not a traced python (a shell, git, node, Chrome, ctypes) - "U"; a python child is counted ("P")
#     and must say hello ("H") itself, or the trace is incomplete (a child started with -I / -S / a scrubbed env);
#   · no hello from the law itself, a run that timed out or a signal ended, an unreadable log, Windows, a law that asks
#     his live console (needs_app), HEART2_TRACE=0;
#   · ANY run of that law in this process that was incomplete (the union is per law file, over every run: the clean
#     wave, the clean run, the narrowed pair, each tamper) - so the set dropped is never wider than what EVERY run saw.
#   Basenames, not paths: a file opened through a dir_fd, a symlink or another copy of the tree still counts as read.
# ⚠ COMPATIBLE: a proof with nothing to drop keeps the v1 key byte for byte, so every PROVEN banked before this serves.
# The laws: test_a_proven_verdict_is_reused_only_on_identical_bytes (P3) and test_a_named_file_the_law_never_opened_is
# _keyed_by_name (this block). [[regression-guard]] [[unknown-stays-unknown]]
_TRACE_SITE_SRC = r'''# heart2 P3-fine read trace (REG-2640). Installed only for a push-time law run, through PYTHONPATH.
import os as _o, sys as _s
def _h2_install():
    log = _o.environ.get("HEART2_TRACE_LOG")
    site = _o.environ.get("HEART2_TRACE_SITE")
    if site:      # leave sys.path as the law would see it, then hand over to any sitecustomize this one shadows
        _s.path[:] = [p for p in _s.path if _o.path.normpath(p or ".") != _o.path.normpath(site)]
    if not log:
        return
    if getattr(_s, "_h2_trace_on", False):   # H2-INSTALL-ONCE: a law run under an OUTER trace chains into its site,
        return                               # which would hook this process twice and count each child twice
    try:
        fd = _o.open(log, _o.O_WRONLY | _o.O_APPEND | _o.O_CREAT, 0o600)
    except OSError:
        return
    import threading as _t
    busy = _t.local()
    _write, _fspath, _base, _real, _isabs, _join, _getcwd = (
        _o.write, _o.fspath, _o.path.basename, _o.path.realpath, _o.path.isabs, _o.path.join, _o.getcwd)

    def emit(tag, txt=""):
        try:
            _write(fd, ("%s %s\n" % (tag, str(txt).replace("\n", " "))).encode("utf-8", "replace"))
        except Exception:
            pass

    def names(tag, path, follow=True):
        if getattr(busy, "on", False):
            return
        busy.on = True
        try:
            if isinstance(path, int) or path is None:
                return
            p = _fspath(path)
            if isinstance(p, bytes):
                p = p.decode("utf-8", "surrogateescape")
            p = str(p)
            emit(tag, _base(p.rstrip("/")))
            if p.endswith(".pyc"):      # a module loaded from its cache read its SOURCE's bytes, at one remove
                emit(tag, _base(p).split(".", 1)[0] + ".py")
            if not follow:               # a caller that is not itself a stat must not resolve (see the wraps below)
                return
            try:
                if not _isabs(p):
                    p = _join(_getcwd(), p)
                emit(tag, _base(_real(p).rstrip("/")))
            except Exception:
                pass
        except Exception:
            emit("U", "unreadable path in " + tag)
        finally:
            busy.on = False

    def pyish(exe, env, argv=None):
        try:
            b = _base(str(_fspath(exe)))
        except Exception:
            return False
        if not b.lower().startswith("python"):
            return False
        try:     # -I / -S / -E: a python that never loads this file (or ignores PYTHONPATH) is not traced
            for a in (list(argv)[1:] if isinstance(argv, (list, tuple)) else []):
                a = str(_fspath(a)) if not isinstance(a, bytes) else a.decode("utf-8", "replace")
                if not a.startswith("-") or a in ("-c", "-m", "-") or a.startswith("--"):
                    break
                if set(a[1:]) & set("ISE"):
                    return False
                if a[1:2] in ("c", "m", "W", "X") and len(a) > 2:
                    break
        except Exception:
            return False
        if env is None:
            return True
        try:
            pp = env.get("PYTHONPATH") or env.get(b"PYTHONPATH") or ""
            pp = pp.decode("utf-8", "replace") if isinstance(pp, bytes) else str(pp)
            return site is not None and site in pp.split(_o.pathsep) \
                and bool(env.get("HEART2_TRACE_LOG") or env.get(b"HEART2_TRACE_LOG"))
        except Exception:
            return False

    def _eget(src, k):
        try:
            v = src.get(k)
        except Exception:
            v = None
        if v is None:
            try:
                v = src.get(k.encode())
            except Exception:
                v = None
        return v.decode("utf-8", "replace") if isinstance(v, bytes) else (str(v) if v is not None else "")

    def nodeish(exe, env, argv=None):
        # REG-3319 - a node child that inherits node_trace.cjs (NODE_OPTIONS) and this same log says its own hello, so it is
        # counted like a python child; one that does not inherit both is not traced (U), and the hello count is the check
        try:
            b = _base(str(_fspath(exe)))
        except Exception:
            return False
        if b not in ("node", "nodejs"):
            return False
        src = env if env is not None else _o.environ
        return "node_trace.cjs" in _eget(src, "NODE_OPTIONS") and _eget(src, "HEART2_TRACE_LOG") == log

    def node_version_only(exe, argv):
        # `node --version` exits before NODE_OPTIONS loads any preload (REG-3127): it reads nothing and never says hello
        try:
            b = _base(str(_fspath(exe)))
            a = [str(_fspath(x)) for x in list(argv)[1:]] if isinstance(argv, (list, tuple)) else None
        except Exception:
            return False
        return b in ("node", "nodejs") and a in (["--version"], ["-v"])

    # the process-table and clock tools a law asks about ITS OWN machine: none of them opens a file of the tree,
    # whatever it is handed (no shell, no interpreter, nothing that takes a path to read)
    _PURE = frozenset(("ps", "pgrep", "kill", "uname", "sysctl", "sw_vers", "true", "false", "sleep", "id", "whoami",
                       "hostname", "date", "nproc", "getconf", "vm_stat", "tty",
                       # v3882 (REG-3393) - the process table and the dynamic-linker cache, never a file of the tree
                       "lsof", "ldconfig"))
    # v3882 (REG-3393) - NARROW KEYS. MEASURED on v3879's round (22 shards): 320 of 520 law files could not be traced, and
    # each kept a byte-for-byte key over its whole closure - a one-file test edit re-proved 4,419 proofs. These are the
    # causes that never read a byte of the tree, each admitted ONLY in the shape that cannot:
    #   * Pillow's image codecs and band maths (PIL._imaging/_webp/_avif/_imagingmath/_imagingmorph) work on BYTES and
    #     bands handed in from Python - an image opened by path is
    #     opened by builtins.open, which this hook sees. Not _imagingft (a font by path, in C) nor _imagingcms (a profile
    #     by path, in C): those still keep every byte. numpy still keeps every byte (fromfile opens a path in C).
    #   * a ctypes library loaded by bare name or from the system, and only the symbols below: process-table, clock and
    #     disk-metadata calls - none takes a path whose BYTES it reads. Any other symbol keeps every byte.
    #   * git, in a directory the parent judges (G line): only one inside the temp dir and outside the sandbox - the law's
    #     own fixture repo - with nothing redirecting git and no path argument leaving that directory.
    _NATIVE_OK = ("_imaging.", "_webp.", "_avif.", "_imagingmath.", "_imagingmorph.")   # image bytes and bands only
    _SYM_OK = frozenset(("prctl", "getrusage", "getpid", "getppid", "sysctl", "sysctlbyname", "clock_gettime",
                         "sched_getaffinity", "getpriority", "setpriority", "mach_task_self", "task_threads", "thread_info",
                         "vm_deallocate", "mach_port_deallocate", "CFRelease", "CFNumberGetValue",
                         "CFURLCreateFromFileSystemRepresentation", "CFURLCopyResourcePropertyForKey", "_important_key"))
    _SYS_LIB = ("/usr/", "/lib/", "/lib64/", "/System/", "/Library/", "/opt/homebrew/", "/nix/store/")
    _GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")

    def native_ok(filename):
        try:
            f = _real(str(_fspath(filename)))
        except Exception:
            return False
        b = _base(f)
        return (_o.sep + "PIL" + _o.sep) in f and b.startswith(_NATIVE_OK)

    def git_dir(cwd, argv, env):
        """-> the real directory this git child works in, or None when it may leave it (U)"""
        src = env if env is not None else _o.environ
        if any(_eget(src, k) for k in _GIT_ENV):
            return None
        try:
            here = str(_fspath(cwd)) if cwd is not None else _getcwd()
            if isinstance(here, bytes):
                here = here.decode("utf-8", "surrogateescape")
            a = [x.decode("utf-8", "surrogateescape") if isinstance(x, bytes) else str(_fspath(x))
                 for x in (list(argv)[1:] if isinstance(argv, (list, tuple)) else [])]
        except Exception:
            return None
        i, d = 0, here
        while i < len(a):
            x = a[i]
            if x == "-C" and i + 1 < len(a):
                d = a[i + 1] if _isabs(a[i + 1]) else _join(d, a[i + 1])
                i += 2
                continue
            if x.startswith(("--git-dir", "--work-tree", "--namespace", "--exec-path")) or x == "--no-index":
                return None
            if x == "-c":
                i += 2
                continue
            if not x.startswith("-"):
                break
            i += 1
        d = _real(d)
        for x in a[i:]:
            if x == "--no-index":
                return None
            if (_isabs(x) or ".." in x.replace("\\", "/").split("/")) and not x.startswith("-"):
                full = _real(x if _isabs(x) else _join(d, x))
                if not (full == d or full.startswith(d.rstrip(_o.sep) + _o.sep)):
                    return None
        return d

    def _shell_ish(argv):
        return not isinstance(argv, (list, tuple))      # a string command line runs through a shell

    _stdlib = _o.path.realpath(_o.path.dirname(_o.__file__))

    def native(filename):
        # a C extension outside the standard library may open a path in C (cv2.imread), where no audit event fires
        try:
            f = str(_fspath(filename))
        except Exception:
            return True
        if not f.endswith((".so", ".pyd", ".dylib")):
            return False
        r = _real(f)
        return not r.startswith(_stdlib + _o.sep) or "site-packages" in r or "dist-packages" in r

    def by_importer():
        # REG-2944 - the import system lists sys.path dirs to find modules; those listings are not the law's own
        try:
            f = _s._getframe(2)
        except Exception:
            return False
        n = 0
        while f is not None and n < 12:
            c = f.f_code.co_filename
            if c.startswith("<frozen importlib") or c.endswith(("importlib/_bootstrap_external.py", "pkgutil.py",
                                                                "zipimport.py")):
                return True
            f = f.f_back
            n += 1
        return False

    def listing(path):
        # REG-2944 - a directory the run LISTED, by its full real path: the proof's key holds what it held
        if getattr(busy, "on", False):
            return
        busy.on = True
        try:
            if isinstance(path, int):
                emit("U", "a listing by file descriptor")
                return
            p = "." if path is None else _fspath(path)
            if isinstance(p, bytes):
                p = p.decode("utf-8", "surrogateescape")
            p = str(p)
            if not _isabs(p):
                p = _join(_getcwd(), p)
            emit("L", _real(p))
        except Exception:
            emit("U", "unreadable path in a listing")
        finally:
            busy.on = False

    def hook(ev, args):
        if ev == "import":
            if len(args) > 1 and args[1] is not None and native(args[1]):
                if native_ok(args[1]):
                    emit("A", "native " + _base(str(args[1])))     # v3882 (REG-3393) - a codec: bytes in, never a path
                else:
                    emit("U", "native " + _base(str(args[1])))
        elif ev == "open":
            names("R", args[0] if args else None)
        elif ev == "sqlite3.connect":
            names("R", args[0] if args else None)
        elif ev == "subprocess.Popen":
            busy.popen = True          # the os.posix_spawn / fork_exec this Popen makes next is this same child
            exe, argv = args[0], args[1]
            if exe is None and argv:
                exe = argv[0] if isinstance(argv, (list, tuple)) else str(argv).split()[0]
            try:
                what = _base(str(_fspath(exe)))
            except Exception:
                what = "?"
            if pyish(exe, args[3] if len(args) > 3 else None, argv):
                emit("P", "spawn " + what)
            elif node_version_only(exe, argv):
                emit("A", "spawn " + what)      # REG-3319 - reads nothing; exits before any preload
            elif nodeish(exe, args[3] if len(args) > 3 else None, argv):
                emit("P", "spawn " + what)      # REG-3319 - a traced node child: counted, says its own hello
            elif what in _PURE and not _shell_ish(argv):
                emit("A", "spawn " + what)      # reads no file of the tree, whatever its arguments
            elif what in ("git", "git.exe") and not _shell_ish(argv):
                _gd = git_dir(args[2] if len(args) > 2 else None, argv, args[3] if len(args) > 3 else None)
                if _gd:
                    busy.gitok = True
                    emit("G", _gd)              # v3882 (REG-3393) - the parent decides: the law's own temp repo, or U
                else:
                    emit("U", "spawn git")
            else:
                emit("U", "spawn " + what)
        elif ev == "os.exec":
            emit("P" if (pyish(args[0], args[2] if len(args) > 2 else None, args[1])
                         or nodeish(args[0], args[2] if len(args) > 2 else None, args[1])) else "U", ev)
        elif ev == "os.posix_spawn":   # subprocess raises this too, after its own Popen event: never counted twice
            try:
                what = _base(str(_fspath(args[0])))
            except Exception:
                what = "?"
            mine = getattr(busy, "popen", False)
            busy.popen = False
            py = (pyish(args[0], args[2] if len(args) > 2 else None, args[1])
                  or nodeish(args[0], args[2] if len(args) > 2 else None, args[1]))     # REG-3319
            _gitok = getattr(busy, "gitok", False)
            busy.gitok = False
            if mine and (py or what in _PURE or node_version_only(args[0], args[1])
                         or (_gitok and what in ("git", "git.exe"))):
                emit("p", ev + " " + what)          # its Popen line already counted it (a G line, for git)
            else:                                  # a direct os.posix_spawn: a python child is counted, all else U
                emit("P" if py else "U", ev + " " + what)
        elif ev in ("os.listdir", "os.scandir"):
            if not by_importer():
                listing(args[0] if args else None)
        elif ev in ("glob.glob", "glob.glob/2"):
            pat = args[0] if args else None
            if isinstance(pat, (str, bytes)):
                pat = pat.decode("utf-8", "surrogateescape") if isinstance(pat, bytes) else pat
                listing(_o.path.dirname(pat) or ".")
        elif ev == "ctypes.dlopen":
            # v3882 (REG-3393) - a library by bare name or from the system loads no byte of the tree
            try:
                nm = args[0] if args else None
                nm = nm.decode("utf-8", "surrogateescape") if isinstance(nm, bytes) else (None if nm is None else str(nm))
            except Exception:
                nm = "?"
            if nm is None or (_o.sep not in nm and "/" not in nm) or _real(nm).startswith(_SYS_LIB):
                emit("A", ev + " " + _base(nm or "self"))
            else:
                emit("U", ev + " " + _base(nm))
        elif ev == "ctypes.dlsym":
            try:
                sym = args[1] if len(args) > 1 else None
                sym = sym.decode("utf-8", "replace") if isinstance(sym, bytes) else str(sym)
            except Exception:
                sym = "?"
            # v3882 (REG-3393) - only calls that read no file; a CoreFoundation kCF... name is a constant (data), never a call
            emit("A" if (sym in _SYM_OK or sym.startswith("kCF")) else "U", ev + " " + sym)
        elif ev in ("os.system", "os.spawn", "os.startfile", "os.forkpty"):
            emit("U", ev)

    for n in ("stat", "lstat", "access", "readlink"):
        f = getattr(_o, n, None)
        if f is None:
            continue
        def wrap(f=f, n=n):
            def w(path, *a, **k):
                # REG-2293 r6 (C): access and readlink are probes of their own. Resolving them calls
                # os.lstat, and a gate probe already owns that name, so the file stayed a ledger input
                # after the probe was removed (carried-law [65] and the readlink sibling).
                names("S", path, n in ("stat", "lstat"))
                return f(path, *a, **k)
            w.__name__ = n
            w.__wrapped__ = f
            return w
        setattr(_o, n, wrap())
    _scandir = getattr(_o, "scandir", None)
    if _scandir is not None:     # a DirEntry's stat() reveals a size without an open: it counts as a stat
        class _Entry(object):
            __slots__ = ("_e",)
            def __init__(self, e):
                self._e = e
            def stat(self, *a, **k):
                names("S", self._e.path)
                return self._e.stat(*a, **k)
            def __getattr__(self, n):
                return getattr(self._e, n)
            def __fspath__(self):
                return self._e.__fspath__()
            def __repr__(self):
                return repr(self._e)
        class _It(object):
            def __init__(self, it):
                self._it = it
            def __iter__(self):
                return self
            def __next__(self):
                return _Entry(next(self._it))
            def __enter__(self):
                return self
            def __exit__(self, *a):
                self.close()
            def close(self):
                c = getattr(self._it, "close", None)
                if c:
                    c()
        def scandir(*a, **k):
            return _It(_scandir(*a, **k))
        scandir.__wrapped__ = _scandir
        _o.scandir = scandir
    try:     # multiprocessing and subprocess start children through fork_exec; nothing else should
        import _posixsubprocess as _ps
        _fe = _ps.fork_exec
        def fork_exec(*a, **k):
            mine = getattr(busy, "popen", False)
            busy.popen = False
            if not mine:
                try:
                    exe = a[0][0] if a and a[0] else None
                    emit("P" if pyish(exe, None, None) else "U", "fork_exec " + _base(str(_fspath(exe))))
                except Exception:
                    emit("U", "fork_exec ?")
            return _fe(*a, **k)
        _ps.fork_exec = fork_exec
    except Exception:
        pass
    for _m in list(_s.modules.values()):        # an extension loaded before this file ran
        if native(getattr(_m, "__file__", None) or ""):
            emit("A" if native_ok(_m.__file__) else "U", "native " + _base(_m.__file__))
    emit("H", "%d %d" % (_o.getpid(), _o.getppid()))
    _s.addaudithook(hook)
    _s._h2_trace_on = True                   # H2-INSTALL-ONCE - only once the hook is really in
try:
    _h2_install()
finally:
    del _h2_install
    try:     # the sitecustomize this one shadowed, if any - found AFTER every one already running, never by re-import:
        import importlib.machinery as _im, importlib.util as _iu   # a gate_trace site that chained HERE would boot twice
        _skip = {_o.path.dirname(_o.path.abspath(f)) for f in (globals().get("__file__"),
                 getattr(_s.modules.get("sitecustomize"), "__file__", None)) if f}
        _f = _s._getframe()   # H2-CHAIN-ONCE: every sitecustomize on the stack (gate -> mid -> here) is already running
        while _f is not None:
            if _o.path.basename(_f.f_code.co_filename) == "sitecustomize.py":
                _skip.add(_o.path.dirname(_o.path.abspath(_f.f_code.co_filename)))
            _f = _f.f_back
        del _f
        _gt = lambda p: _o.path.isfile(_o.path.join(p or ".", "node_trace.cjs"))   # a gate_trace copy (TRACE-CHAIN-ONCE)
        _ran = any(_gt(d) for d in _skip)       # one already runs (it chained HERE): never boot another copy; else the
        _nxt = _im.PathFinder.find_spec("sitecustomize", [p for p in _s.path if _o.path.abspath(p or ".") not in _skip
                                        and not (_ran and _gt(p))])   # first one still loads - the kill watch arms
    except Exception:
        _nxt = None
    if _nxt is not None and _nxt.loader is not None:   # a successor that raises propagates, as `import` did
        _nxt.loader.exec_module(_iu.module_from_spec(_nxt))
'''
_TRACES = {}                     # law filename -> {"names": set(basenames), "ok": bool, "runs": int}, this process only
_TRACE_LOCK = threading.Lock()
_TRACE_WHY = []                  # why a run was not fully traced (the U lines), last 200, for the measurement
_TRACE_DIR = {"path": None}


def _trace_site():
    """REG-2640 - the directory holding the trace sitecustomize, written once per process. -> path | None"""
    with _TRACE_LOCK:
        d = _TRACE_DIR["path"]
        if d and os.path.isfile(os.path.join(d, "sitecustomize.py")):
            return d
        _trace_sweep()
        try:
            d = tempfile.mkdtemp(prefix="heart2-trace-%d-" % os.getpid())
            with io.open(os.path.join(d, "sitecustomize.py"), "w", encoding="utf-8") as fh:
                fh.write(_TRACE_SITE_SRC)
            atexit.register(shutil.rmtree, d, True)
        except OSError:
            return None
        _TRACE_DIR["path"] = d
        return d


def _trace_sweep(base=None):
    """REG-2640 - a prover KILLED by SIGKILL never reaches atexit: its trace dir (the sitecustomize and every run's
    log) would stay in the temp dir for good. Remove those whose owner pid is dead. -> [removed names]"""
    base = base or tempfile.gettempdir()
    gone = []
    try:
        names = os.listdir(base)
    except OSError:
        return gone
    for n in names:
        if not n.startswith("heart2-trace-"):
            continue
        try:
            pid = int(n[len("heart2-trace-"):].split("-", 1)[0])
        except ValueError:
            continue
        if pid != os.getpid() and not _pid_alive(pid):
            shutil.rmtree(os.path.join(base, n), ignore_errors=True)
            gone.append(n)
    return gone


def _trace_wanted(filename, env=None):
    """REG-2640 - is this law run traced? Push time with the verdict cache open, POSIX, not a live-console law."""
    env = os.environ if env is None else env
    if env.get("HEART2_TRACE") == "0" or os.name != "posix":
        return False
    if _PUSH is None or getattr(_PUSH, "cache", None) is None:
        return False
    try:
        import run_gates as _rg_t
        return not _rg_t.needs_app_of(filename)
    except Exception:
        return False


def _trace_read(log, root_ppid, listed=None, why=None, sandbox=None):
    """REG-2640 - one traced run's log. -> (basenames read or stat'd, complete: bool). REG-2944 - the full real path of
    every directory the run listed is added to `listed` when a set is handed in. REG-3319 - and WHY a run was not
    complete is added to `why` (the untraced child, a missing hello), so a round can say what keeps keys wide."""
    seen, hellos, root, py, untraced = set(), set(), False, 0, False
    try:
        with io.open(log, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                tag, _sp, rest = ln.rstrip("\n").partition(" ")
                if tag in ("R", "S"):
                    seen.add(rest)
                elif tag == "H":
                    parts = rest.split()
                    if len(parts) == 2 and parts[1] == str(root_ppid) and not root:
                        root = parts[0]
                    elif parts and parts[0] != root:
                        hellos.add(parts[0])     # one per PROCESS: a hello said twice never stands for a silent child
                elif tag == "P":
                    py += 1
                elif tag in ("p", "A"):
                    pass
                elif tag == "N":                 # REG-3319 - a node child ran: no JavaScript-family input is dropped
                    seen.add(_NODE_MARK)
                elif tag == "G":                 # v3882 (REG-3393) - a git child, in the directory it named
                    _gw = _git_child_why(rest, sandbox)
                    if _gw:
                        untraced = True
                        _TRACE_WHY.append(_gw[:60])
                        del _TRACE_WHY[:-200]
                        if why is not None:
                            why.add(_gw[:60])
                elif tag == "L":                 # REG-2944 - a listing, by full path
                    if listed is not None:
                        listed.add(rest)
                elif tag:
                    untraced = True
                    _TRACE_WHY.append(rest[:60])
                    del _TRACE_WHY[:-200]
                    if why is not None:
                        why.add(rest[:60])
    except OSError:
        if why is not None:
            why.add("its trace log would not read")
        return seen, False
    if why is not None:
        if not root:
            why.add("the law itself said no hello")
        if len(hellos) < py:
            why.add("a child said no hello")
    return seen, bool(root and not untraced and len(hellos) >= py)


def _git_child_why(gdir, sandbox):
    """v3882 (REG-3393) - may a git child working in `gdir` (a real path the child resolved) be traced past? -> None (it
    reads only the law's own fixture repo) | why it keeps every byte. Only a directory inside the temp dir and OUTSIDE the
    sandbox passes: the sandbox IS the tree (and lives in the temp dir too), and his real repo is outside the temp dir."""
    if not gdir or not os.path.isabs(gdir):
        return "spawn git (no directory)"
    if not sandbox:
        return "spawn git (no sandbox to judge it by)"
    g = os.path.realpath(gdir)
    sb = os.path.realpath(sandbox)
    tmp = os.path.realpath(tempfile.gettempdir())

    def under(p, base):
        return p == base or p.startswith(base.rstrip(os.sep) + os.sep)
    if under(g, sb) or under(sb, g):
        return "spawn git in the tree"
    if not under(g, tmp):
        return "spawn git outside the temp dir"
    return None


def _trace_record(filename, seen, ok, listed=None, why=None):
    with _TRACE_LOCK:
        t = _TRACES.setdefault(filename, {"names": set(), "ok": True, "runs": 0})
        t["names"] |= seen
        t["ok"] = bool(t["ok"] and ok)
        t["runs"] += 1
        if not ok:      # REG-3319 - why this law keeps its byte-for-byte key, for the round's RECORD line
            t.setdefault("why", set()).update(why or ("UNKNOWN - no cause was read",))
        t.setdefault("listed", set()).update(listed or ())     # REG-2944 - every dir any traced run of it listed


def _trace_why_census():
    """REG-3319 - this process's traced law files: how many traced completely, and why the rest did not (per law file, a
    cause counted once; 'spawn X' keeps the program's name). -> {"laws", "ok", "causes": [(cause, n)]} | None"""
    with _TRACE_LOCK:
        rows = [(bool(t.get("ok")) and t.get("runs", 0) > 0, set(t.get("why") or ())) for t in _TRACES.values()]
    if not rows:
        return None
    causes = {}
    for ok, why in rows:
        if ok:
            continue
        for w in (why or {"UNKNOWN - no cause was read"}):
            k = " ".join(str(w).split()[:3])
            causes[k] = causes.get(k, 0) + 1
    return {"laws": len(rows), "ok": sum(1 for ok, _w in rows if ok),
            "causes": sorted(causes.items(), key=lambda kv: (-kv[1], kv[0]))}


_NODE_MARK = "\x00node-ran"     # REG-3319 - a name no file has: "a node child of this law ran" (see _trace_unread)
#: REG-3319 - what a node module loader may read past fs on some node version (an ES module's static imports, JSON
#: modules, wasm): once a node child ran, these are never dropped, whatever the trace saw
_NODE_KEEP_EXT = (".js", ".mjs", ".cjs", ".json", ".ts", ".tsx", ".wasm", ".node")


def _trace_unread(filename, rels, keep):
    """REG-2640 - the inputs of `rels` (repo-relative) this law's traced runs never opened or stat'd. -> sorted list
    ([] when any run of it was not fully traced, or none ran). `keep` are never dropped (target, PROOF_NEEDS, prover)."""
    with _TRACE_LOCK:
        t = _TRACES.get(filename)
        if not t or not t["ok"] or t["runs"] < 1:
            return []
        names = set(t["names"])
    node_ran = _NODE_MARK in names
    return sorted(r for r in rels if r not in keep
                  and r.rsplit("/", 1)[-1] not in names
                  and not (node_ran and r.lower().endswith(_NODE_KEEP_EXT)))


# ══ REG-2944 (REG-2296 for the PROOF cache) — A LAW THAT LISTS A DIRECTORY IS KEYED BY WHAT ITS TRACED RUN LISTED ═════
# A law file that calls os.listdir / os.walk / glob was UNKEYABLE: what it reads is decided at run time (tv/unkeyable_laws
# - 63 laws, many of them censuses whose denominator IS a tree folder). gate_ledger keys such a gate's PASS by what its
# traced run listed (REG-2296); this is the same move for a PROOF. The REG-2640 trace now also records every directory a
# run LISTS (os.listdir / os.scandir, and glob's own event), by its full real path - never the import system's listings
# of sys.path. A listing law's PROVEN is banked under a v3 key: its v1/v2 material plus, for each directory any traced
# run of it listed, the sorted names that directory holds and the bytes of each file among them. So an added, removed or
# changed file in a listed directory is a new key, and nothing else is.
#   ⚠ ONLY LAWS THAT LIST IN THE LAW FILE. A law that lists only through its closure (gate_files() and the like) keeps its
#     v1/v2 key byte for byte - THE CLOSURE-LISTING FLOOR, a decision: keying those would re-key nearly every heart law
#     on any tv/ change and cost the wall clock this exists to save. Stated in BUGS REG-2944.
#   ⚠ GITIGNORED ENTRIES of a listed directory are not key material (#242's rule: runtime data is never a key input) - and
#     a run that READ or STAT'ed one of them is never banked, so content from runtime data never stands under a key.
#   ⚠ A listing OUTSIDE the tree - his home, /proc, the shared temp dir - is never banked; a listing inside the run's own
#     fixture_tmp scratch adds nothing (the code that made it is keyed). An incomplete trace banks nothing.
# Laws: test_a_listing_law_is_keyed_by_what_it_listed.
_OWN_SCRATCH_PREFIX = "d2r-test-"        # fixture_tmp.PREFIX: a contained test scratch parent
_OWN_SCRATCH_RX = re.compile(r"^d2r-test-\d+-")   # its name, as fixture_tmp.contain() makes it: <prefix><pid>-<random>


def _trace_listed(filename, repo, ignored_names=None):
    """REG-2944 - the repo-relative directories this law's traced runs listed. -> (sorted rels, None) | (None, why)

    None when any run was not fully traced or none ran, when a listing left the tree (anything but the repo and the run's
    own contained scratch), or when a run read or stat'ed a gitignored entry of a directory it listed
    (`ignored_names(rel_dir)` -> the gitignored names in it)."""
    with _TRACE_LOCK:
        t = _TRACES.get(filename)
        if t is None or not t["ok"] or t["runs"] < 1:
            return None, "no complete trace of it"
        listed, names = set(t.get("listed") or ()), set(t["names"])
    root = os.path.realpath(repo)
    rels = set()
    for d in sorted(listed):
        if d == root or d.startswith(root + os.sep):
            rels.add(os.path.relpath(d, root).replace(os.sep, "/"))
            continue
        if any(_OWN_SCRATCH_RX.match(part) for part in d.split(os.sep)):
            continue                                  # its own contained scratch: made by code the key already holds
        return None, "it listed a directory outside the tree (%s)" % os.path.basename(d)
    if ignored_names is not None:
        for rel in sorted(rels):
            got = ignored_names(rel)
            if got is None:
                return None, "git could not say which entries of %s are runtime data" % rel
            hit = sorted(set(got) & names)
            if hit:
                return None, "it read %s, a gitignored file in %s it listed" % (hit[0], rel)
    return sorted(rels), None


def _kept_files(repo=None):
    """REG-2944 - the repo-relative paths git does NOT ignore and does not track (a new law not yet added). -> frozenset |
    None (UNKNOWN). With _tracked_files, what a listed directory's key holds; everything else in it is runtime data."""
    repo = REPO if repo is None else repo
    try:
        import git_quiet as _gq
        r = _gq.run(["git", "-C", repo, "ls-files", "-z", "--others", "--exclude-standard"],
                           capture_output=True, timeout=30, env=_git_free_env())
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return frozenset(x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x)


# ══ REG-2350 (#42 R5) — A RUN A SIGNAL ENDED IS UNKNOWN, NEVER A RED ═══════════════════════════════════════════════════
# _run_gate_once returned `returncode == 0`, so a law process killed by a signal (-9 from reap's by-pid kill or jetsam,
# -2 from a Ctrl-C) read as RED: in a tampered run that is PROVEN, banked after a green closing run, a lie standing until
# an input moves; in a clean run it is ALREADY RED and refuses a good push. Two more shapes read the same: a shell that
# reports a child killed by signal N exits 128+N, and a GRANDCHILD killed by a signal (a headless Chrome, the node demo,
# a python helper) makes the law exit 1 with an ERROR case. So, before any verdict is read:
#   · the law process ended by a signal (a negative code), or exited 128+N for a signal N that ends a run from outside
#     (_SHELL_SIGNALS - heart2's own handlers exit 128+N for SIGTERM/SIGALRM/SIGHUP/SIGINT the same way) -> UNKNOWN;
#   · the kill watch (gate_trace/sitecustomize.py, armed here by TV_GATE_KILLS) saw a child of the run end by a signal
#     that no process of the run SENT (a K line no X line explains; SIGPIPE, a closed pipe, is not a kill) -> UNKNOWN.
# A law that kills its own LIVE child (terminate, kill, killpg - the X line) is judged exactly as before. REG-2356: a
# signal sent to a child that was already dead explains nothing. That is a teardown signalling a helper a kill from
# outside had already ended, which once banked a BLIND law PROVEN. Nor does a signal sent after the death was reaped,
# one of another number, or one sent before an earlier END of that pid - a death or any exit, or the pid left to init
# when its parent exited (REG-2358: the pid was recycled, so it is a new process) - see _kills_in.
# UNKNOWN is never banked, never a stop, and the narrow path and the closing run both fall through on it. Counted for
# the push record. The law: test_a_killed_run_is_never_a_red.
# ⚠ A NEVER-WRONG HOLE THIS LEAVES OPEN, ON EVERY OS (pre-existing; measured by the round-4 review): the 128+N rule reads
#   only the LAW's own exit code, and the watch sees only children that a TRACED python process started through
#   subprocess.Popen. Any other descendant killed from outside writes no K line - a shell helper's job (the shell then
#   exits 137: an E line, not a death), a non-python child's own children (a Python-Playwright law's Chrome under its
#   node driver, Chrome's renderers), a multiprocessing worker, a child of a python run with -I/-E or a scrubbed
#   PYTHONPATH. That run ends with an ordinary code, this returns a VERDICT, and a tampered run that is red only because
#   of that outside kill is PROVEN and banked. origin/main reads EVERY kill that way; this narrows it to those
#   descendants, it does not close it. Open in BUGS.md REG-2350 LEFT, beside Windows' terminate-code hole.
# [[unknown-stays-unknown]]
_SHELL_SIGNALS = (1, 2, 6, 9, 14, 15)
_SIGNAL_RUNS = {"n": 0}
_SIGNAL_LOCK = threading.Lock()
_KILL_LINE = re.compile(r"^([KXE])\t\d+\t(.*)$")
_KILL_FIELD = re.compile(r"(\w+)=(\S+)")
#: REG-2359 — the skip watch's line (gate_trace/sitecustomize.py): one per case the run's own process skipped
_SKIP_LINE = re.compile(r"^O\t\d+\tcase=(\S*) reason=(.*)$")
#: REG-2359 — thread id -> the skips of that thread's last run, [(case id, reason)] ([] none; None: no watch could say).
#: A side channel like _LAST_RED, so a stand-in _run_gate stays valid.
_LAST_SKIPS = {}


def _signal_words(n):
    """'signal 9 (SIGKILL)' -> str"""
    try:
        import signal as _sg
        return "signal %d (%s)" % (int(n), _sg.Signals(int(n)).name)
    except Exception:
        return "signal %s" % (n,)


def _ended_by_signal(rc):
    """REG-2350 — the signal a law's exit code says ended it, or None. -> (n, words) | None"""
    if not isinstance(rc, int) or isinstance(rc, bool):
        return None
    if rc < 0:
        return -rc, "the law was killed by %s" % _signal_words(-rc)
    if rc - 128 in _SHELL_SIGNALS:
        return rc - 128, "the law exited %d, a shell's word for a child killed by %s" % (rc, _signal_words(rc - 128))
    return None


def _kill_watch(env):
    """REG-2350 — arm gate_trace/sitecustomize.py's kill watch in a run's environment. -> the watch file | None

    The prover's OWN copy of the hook (HERE, never the sandbox's): a proof that tampers the hook in its sandbox must not
    blind the watch over its own run."""
    try:
        fd, path = tempfile.mkstemp(prefix="heart2-kills.", suffix=".tsv")
        os.close(fd)
    except OSError:
        return None
    env["TV_GATE_KILLS"] = path
    env["TV_GATE_SKIPS"] = "1"                # REG-2359 - and the run's own process writes the reason of every skip
    hook_dir = os.path.join(HERE, "gate_trace")
    old = env.get("PYTHONPATH") or ""
    if hook_dir not in old.split(os.pathsep):
        env["PYTHONPATH"] = hook_dir + (os.pathsep + old if old else "")  # KILL-WATCH-ARM
    return path


def _kills_in(path):
    """REG-2350 — the K lines of one run's kill watch that no X line of the SAME run explains. -> [{pid, pgid, sig, head}]

    Explained: a signal some process of the run sent to that pid, to its group (a group leader's pid is its pgid), or to
    every process. SIGPIPE is a reader that closed its end, not a kill. A watch file nobody can read is no K line: the
    watch adds UNKNOWNs, it never grants a verdict.

    REG-2356 — and only by an X that could have caused that death. Before, any X to the same pid or group explained a K,
    so a helper killed from OUTSIDE (jetsam, a reap) and then signalled by the law's teardown before it was reaped read
    as a death the run caused. The run read red, and a BLIND law was banked PROVEN (measured). Now all of these hold:
      · the X is written ABOVE the K. The hook writes an X before its signal leaves and a K after the death is reaped,
        so a death reaped before the signal was sent was never that signal's doing;
      · the SAME signal: a SIGTERM never explains a SIGKILL death;
      · the X is not `dead=1` (its target was already dead, or a group that pid does not lead), and it does not name
        this pid in `gone=` (a member of the signalled group that was already dead).

    REG-2358 — and only by an X written after that pid's previous END. A pid that ended is a NEW process the next time it
    dies - the pid was recycled - and no signal sent before that end ended the next one, by pid, by group or to every
    process. An end is a K (whether or not anything explains it: a pipe, another signal) or an E: the hook writes E for
    a child that ended WITHOUT a signal - any exit code, reaped by wait, by poll or by Popen's own finalizer when it was
    dropped unwaited - and `rc=left` for a child still running when the process that started it exited (init reaps it,
    so no line of the run will ever say its death). Round 3 let only the first K use up an X's chance at a pid, so a
    helper that handled the law's SIGTERM and exited 0 left that chance open, and the next process to get its pid,
    killed from outside, read as the law's own kill: the run read red, and a tampered run red that way is PROVEN."""
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except (OSError, TypeError) as _we:
        # said, never silent: a watch nobody can read shows no kill, so the run is judged by its own code alone (as
        # before REG-2350) - and a kill from outside it would have seen is the open hole REG-2350 LEFT names
        print("  ⚠ the kill watch could not be read (%s) - this run is judged without it" % type(_we).__name__)
        return []
    try:
        import signal as _sg
        _pipe = int(getattr(_sg, "SIGPIPE", 13))
    except Exception:
        _pipe = 13
    sent, ends = [], []
    for at, ln in enumerate(lines):
        m = _KILL_LINE.match(ln)
        if not m:
            continue
        f = dict(_KILL_FIELD.findall(m.group(2)))
        if m.group(1) == "E":
            f["at"], f["n"] = at, None   # REG-2358: its pid ENDED with no signal - it closes that pid, and is no kill
            ends.append(f)
            continue
        try:
            f["at"], f["n"] = at, int(f.get("sig"))
        except (TypeError, ValueError):
            continue  # a line with no signal number explains nothing and is no kill
        if m.group(1) == "K":
            ends.append(f)
            continue
        if f.get("dead") == "1":
            continue  # KILL-WATCH-DEAD-X: it could end nothing, so it explains nothing
        f["all"] = m.group(2).startswith("all")
        f["gone"] = set((f.get("gone") or "").split(","))
        sent.append(f)
    out = []
    last = {}                                            # REG-2358: pid -> the line of its latest END read so far
    for k in ends:                                       # in the order the watch wrote them
        p = k.get("pid")
        before = last.get(p, -1)
        last[p] = k["at"]  # KILL-WATCH-ENDED
        if k["n"] is None:
            continue                                     # an E: nothing ended it, so there is nothing to explain
        # every X above this death that reaches its pid, written after that pid's previous end (sent to THIS process)
        reach = [x for x in sent
                 if x["at"] < k["at"]  # KILL-WATCH-ORDER
                 and x["at"] > before  # KILL-WATCH-FIRST-END
                 and (x["all"] or ("pid" in x and x["pid"] == p)
                      or ("pgid" in x and x["pgid"] in (p, k.get("pgid"))))]
        if k["n"] == _pipe:
            continue
        if any(x["n"] == k["n"]  # KILL-WATCH-SAME-SIGNAL
               and p not in x["gone"]  # KILL-WATCH-GONE-PID
               for x in reach):
            continue  # KILL-WATCH-EXPLAINED
        out.append(dict((key, v) for key, v in k.items() if key not in ("at", "n")))
    return out


def _skips_in(path):
    """REG-2359 — the cases the run's own process skipped and the reason it gave for each (the skip watch's O lines), in
    the order it skipped them. -> [(case id, reason)]; None when the watch file cannot be read (UNKNOWN - never "it
    skipped nothing"). A case id is unittest's own (`__main__.Class.test_x`)."""
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except (OSError, TypeError):
        return None
    return [(m.group(1), m.group(2)) for m in (_SKIP_LINE.match(ln) for ln in lines) if m]


def _run_gate_once(sandbox_tv, filename, timeout=180, extra=(), script=None, widths=None):
    # v2882 — `extra` carries the registered gate's argv tail (e.g. `--selftest`). Without
    # it a gate runs a command the suite never issues, and its verdict is about something
    # else. Default empty keeps every existing caller identical.
    """-> (passed: bool | None, tail: str). None = UNKNOWN: a deadline, a missing file, or a run a signal ended."""
    p = os.path.join(sandbox_tv, filename)
    if not os.path.exists(p):
        return None, "the gate file is not in the sandbox"
    timeout, _bwhy = _inflight_limit(timeout)          # REG-3212 - a run already going is cut at its bound too
    if _bwhy is not None and timeout <= 0:
        _BOUND.cut = _bwhy
        return None, "cut at its bound before it started (%s) - UNKNOWN, never PROVEN" % _bwhy
    env = _git_free_env()                      # REG-2396 - a law run never inherits the caller's GIT_DIR
    env["PYTHONDONTWRITEBYTECODE"] = "1"      # no stale .pyc can outlive a tamper
    env["HEART2_LANES"] = str(int(LANES_NOW or 1))   # REG-1997 - the lanes running beside this law right now
    # ⚠ #42 — THE RESTRICTION BELONGS TO THE PROOF, NEVER TO THE ENVIRONMENT. `widths` is handed in only by a push-time
    # proof that DECLARED them (_prove_push_one); every other run — every run without --push, every proof that declares
    # none, triage — has TV_LAW_WIDTHS REMOVED, so a value left in a shell can never quietly turn a full sweep into a
    # sample that still prints OK. [[regression-guard]]
    env.pop("TV_LAW_WIDTHS", None)
    # REG-1729 (#156) - a law never asks his live console: the same door run_gates uses (a dead free port unless the
    # gate needs his console). A sandboxed proof is a law run like any other.
    import run_gates as _rg_env
    env = _rg_env.law_env(_rg_env.needs_app_of(filename), env)
    # #144 — this lane's own ports. Suites that pin 17971/17972 derive from TV_LANE_PORT_BASE.
    # needs_app keeps whatever law_env left, so a gate that must ask his console still can.
    # No lane (a direct _run_gate, triage) stamps nothing.
    _ln = getattr(_LANE_LOCAL, "n", None)
    if _ln and not _rg_env.needs_app_of(filename):
        env = _stamp_lane_ports(env, _ln)
    if widths:
        import law_widths as _LW
        env[_LW.ENV] = _LW.label(widths)
    # ⚠⚠ v2888 — AN ABSOLUTE ARGUMENT POINTS AT THE REAL TREE, WHICH THE TAMPER NEVER TOUCHED.
    # A gate handed /Users/.../tv/x.py reads the ORIGINAL x.py no matter what this sandbox says,
    # so its proof can only ever come back green. Re-root every repo-absolute argument onto the
    # copy before running. [[feedback-blind-fixture-green-gate]]
    _root = os.path.dirname(os.path.abspath(sandbox_tv))
    def _resite(a):
        if isinstance(a, str) and os.path.isabs(a) and a.startswith(REPO + os.sep):
            return os.path.join(_root, os.path.relpath(a, REPO))
        return a
    _args = [_resite(a) for a in extra]
    _cmd = ([sys.executable, "-c", script] + _args) if script else ([sys.executable, p] + _args)
    _tlog = None
    if _trace_wanted(filename):              # REG-2640 - which files this run opens, for the P3 key
        _tsite = _trace_site()
        if _tsite is None:
            _trace_record(filename, set(), False)
        else:
            _tenv = {k: env.get(k) for k in ("PYTHONPATH", "HEART2_TRACE_LOG", "HEART2_TRACE_SITE")}
            try:
                _tfd, _tlog = tempfile.mkstemp(prefix="h2trace-", suffix=".log", dir=_tsite)
                os.close(_tfd)
                env["PYTHONPATH"] = _tsite + ((os.pathsep + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
                env["HEART2_TRACE_LOG"], env["HEART2_TRACE_SITE"] = _tlog, _tsite
                # REG-3319 - and a node child of the run loads node_trace.cjs, which writes this same log (one hook per
                # process: an outer gate trace that already named it keeps its copy, and that copy sees this log too)
                _ntr = os.path.join(sandbox_tv, "gate_trace", "node_trace.cjs")
                _tenv["NODE_OPTIONS"] = env.get("NODE_OPTIONS")
                if os.path.isfile(_ntr) and "node_trace.cjs" not in str(env.get("NODE_OPTIONS") or ""):
                    import gate_ledger as _GLn   # v3886 (#107) - the one preload spelling: '/' (node reads '\\' as an escape)
                    env["NODE_OPTIONS"] = _GLn.node_require(_ntr) + ((" " + env["NODE_OPTIONS"]) if env.get("NODE_OPTIONS") else "")
            except BaseException:             # REG-2640 - any setup failure: env restored, no log, nothing dropped
                for _k, _v in _tenv.items():
                    if _v is None:
                        env.pop(_k, None)
                    else:
                        env[_k] = _v
                if _tlog is not None:
                    try:
                        os.unlink(_tlog)
                    except OSError:
                        pass
                _tlog = None
                _trace_record(filename, set(), False)
                if not isinstance(sys.exc_info()[1], Exception):
                    raise
    _watch, _killed, _tdone = None, None, False
    try:
        _watch = _kill_watch(env)             # REG-2350 — which children of this run a signal ended, and who sent it
        r = subprocess.run(_cmd, cwd=sandbox_tv, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        _tdone = _ended_by_signal(r.returncode) is None
    except subprocess.TimeoutExpired:
        if _bwhy is not None:                 # REG-3212 - the bound killed it, not the law's own deadline: TIMEOUT
            _BOUND.cut = _bwhy
            return None, "cut at its bound after %d s (%s) - UNKNOWN, never PROVEN" % (int(timeout), _bwhy)
        return None, "timed out after %ss" % timeout
    finally:
        try:
            _killed = _kills_in(_watch) if _watch else []
            _LAST_SKIPS[threading.get_ident()] = _skips_in(_watch) if _watch else None   # REG-2359 - why each case skipped
        finally:
            if _watch:
                try:
                    os.unlink(_watch)
                except OSError:
                    pass
            if _tlog is not None:             # REG-2640 - recorded on every exit; complete only if it ran out, unkilled
                _tseen, _tok, _tls, _twhy = set(), False, set(), set()
                try:
                    _tseen, _tok = _trace_read(_tlog, os.getpid(), listed=_tls, why=_twhy, sandbox=_root)
                finally:
                    if not _tdone:
                        _twhy.add("the run did not end on its own (timeout or a signal)")
                    if _killed:
                        _twhy.add("a child of the run was killed")
                    _trace_record(filename, _tseen, bool(_tok and _tdone and _killed == []), listed=_tls, why=_twhy)
                    try:
                        os.unlink(_tlog)
                    except OSError:
                        pass
    _sig = _ended_by_signal(r.returncode)
    if _sig is not None or _killed:
        # REG-2350 — NOT A VERDICT, before any line of it is read: a signal from outside ended the law or a child of it
        with _SIGNAL_LOCK:
            _SIGNAL_RUNS["n"] += 1
        _k = _killed[0] if _killed else {}
        _why = _sig[1] if _sig is not None else (
            "a child of the run (%s, pid %s) was killed by %s that nothing in the run sent"
            % (_k.get("head") or "?", _k.get("pid") or "?", _signal_words(_k.get("sig"))))
        _tl = ((r.stdout or b"").decode("utf-8", "replace").strip().splitlines() or [""])[-1].strip()[:80]
        return None, "%s - a run a signal ended is UNKNOWN, never a verdict (REG-2350)%s" % (
            _why, (" | last line: %s" % _tl) if _tl else "")
    # ⚠⚠ v2870 — THE LAST LINE ALONE IS A NUMERATOR WITH NO DENOMINATOR. unittest prints
    # "Ran 10 tests in 0.1s", a blank, then "OK (skipped=4)" — and keeping only the last line threw
    # away the one number that says whether a skip covered the WHOLE file or part of it. A
    # cross-family review of v2868: five laws skipping while three run and stay green is a WEAK
    # LAW, and blind_reason was instructing the reader to go delete skips instead.
    # [[zero-needs-a-denominator]]
    # ⚠⚠ v2872 — AND THE RESULT LINE IS NOT ALWAYS LAST EITHER. v2870 fixed the DENOMINATOR by
    # hunting backwards for `Ran N tests` and then kept taking `skipped=K` from whatever printed
    # last — the same last-line bug, applied to the half it was written to interpret. A cross-family
    # review of v2870: one `atexit` print, a DeprecationWarning on stderr (merged here via
    # stderr=STDOUT), any shutdown line, and `OK (skipped=5)` is no longer last. `n_skipped` reads 0
    # and a WHOLE-FILE skip reports as a weak law. Both lines are hunted now, and whatever really
    # printed last is kept beside them, because it may be the actual news.
    # ⚠⚠⚠ v2874 — AND THE RESULT IS THE ONE THAT FOLLOWS `Ran`, NOT THE LAST ONE THAT LOOKS LIKE
    # IT. Third round of this same class, each caught by the cross-family eye and not by me. v2872
    # hunted BACKWARDS for a result-shaped line, so anything printed afterwards that happens to look
    # like a result STEALS it and unittest's real one is dropped from the tail entirely. MEASURED on
    # the v2872 parser, a two-test whole-file skip that should read ALL 2:
    #     atexit print('DeprecationWarning: ...')  -> 'Ran 2 tests | OK (skipped=2) | Deprecation…'  ALL 2   ✔
    #     atexit print('OK')                       -> 'Ran 2 tests | OK'                             no warning ✘
    #     atexit print('FAILED to cleanup')        -> 'Ran 2 tests | FAILED to cleanup'              no warning ✘
    # v2872's own behavioural law could not catch it because its fixture printed a WARNING-shaped
    # line, which the predicate does not match — the blind-fixture shape that commit quoted while
    # shipping it. unittest prints `Ran N tests`, a blank, then the result; noise comes after. So
    # find `Ran` and take the NEXT result line going FORWARD.
    # ⚠ And the two matchers are now symmetric. `FAILED` was a PREFIX while `OK` was exact-or-`OK (`,
    # so `FAILED to cleanup` could steal where `OK to cleanup` could not.
    # [[feedback-generalize-fixes]] [[feedback-blind-fixture-green-gate]]
    def _is_result(s):
        return s in ("OK", "FAILED") or s.startswith("OK (") or s.startswith("FAILED (")
    _lines = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
    _LAST_RED[threading.get_ident()] = _red_ids(_lines)     # #42 lever 1 — which cases went red, for the red memory
    _last = _lines[-1].strip() if _lines else ""
    _ran, _res, _ran_i = "", "", -1
    for _i in range(len(_lines) - 1, -1, -1):
        _s = _lines[_i].strip()
        if _s.startswith("Ran ") and " test" in _s:
            _ran, _ran_i = _s, _i
            break
    if _ran_i >= 0:
        for _l in _lines[_ran_i + 1:]:
            _s = _l.strip()
            if _is_result(_s):
                _res = _s
                break
    _parts = [_p for _p in (_ran, _res) if _p]
    if _last and _last not in _parts:
        _parts.append(_last)
    # REG-1877 (#112) - THE ALT'S LOG KEPT "FAILED (failures=6)" AND NEVER WHICH SIX. A run that went red now carries the NAMES
    # of its red cases after a " | red: " marker, so an UNPROVABLE-untampered row can be read without re-running the suite.
    if r.returncode != 0:
        _ids = _LAST_RED.get(threading.get_ident()) or []
        if _ids:
            _parts.append("red: " + ", ".join(_ids[:12]) + ((" (+%d more)" % (len(_ids) - 12)) if len(_ids) > 12 else ""))
            # v3888 (REG-3479) - AND WHAT IT SAID. test_vault_l1_war_stash_overflow went red untampered on v3881's shard 12,
            # v3882's shard 10 and twice on v3886's shard 13; since REG-1877 the log names the case
            # (WarStashOverflow.test_all_five_pages_fill_then_war1_then_war2) and still never what failed, so three reds and
            # a re-run later the cause was UNKNOWN. The first assertion line rides beside the names (words only).
            for _l in _lines:
                _c = _ANSI_RX.sub("", _l).strip()
                if re.match(r"\w*(?:Error|Exception):", _c):
                    _parts.append("why: " + _c[:240])
                    break
        else:
            # v3882 - A RED THAT NAMES NO CASE STILL SAYS ITS FIRST FAILURE LINE. MEASURED: test_vault_l1_war_stash_overflow
            # went red untampered on v3881's shard 12 and v3882's shard 10 ("Ran 15 tests ... FAILED (failures=1)") and no
            # log named the case either time, so it could not be fixed. Never into the red memory (_LAST_RED): words only.
            _first = ""
            for _l in _lines:
                _c = _ANSI_RX.sub("", _l).strip()
                if re.match(r"(?:FAIL|ERROR):\s", _c) or re.search(r"\b\w*(?:Error|Exception):", _c):
                    _first = _c
                    break
            if _first:
                _parts.append("red: UNNAMED (%s)" % _first[:200])
    return r.returncode == 0, (" | ".join(_parts) if _parts else _last)


# ── the proving loop ─────────────────────────────────────────────────────────────────────────
# ══ HOW MANY PROOFS RUN AT ONCE, AND WHY EVERY LANE GETS ITS OWN SANDBOX ═══════════════════════
# The loop below used to be doubly serial — per gate, then per proof — and one proof is
# "sabotage a file → run that gate in a subprocess → restore". MEASURED on his pushes: this step
# was ~24 min of a 38m42s push and ~26 min of a 41m25s one, 60%+ of EVERY push, with ONE child
# process alive at a time and load ~2.2 on a 10-core machine. It was never CPU-bound. It was
# serialised, and it GROWS with every law added.
#
# ⚠⚠⚠ THE OBVIOUS SPLIT — one worker per GATE inside ONE SHARED sandbox — IS UNSAFE, and this is
# the measurement that settles it, taken 2026-09-23 over the whole registry:
#       537 gate files readable · 497 declare a red-proof · 1,302 declared proofs
#       149 distinct tampered files once resolved · 67 of them claimed by MORE THAN ONE gate
#       446 of 497 gates (90%) tamper a file that another gate also tampers
#       control_app.py alone: 124 gates tamper it — and a further 110 gates NAME it without
#       tampering it at all, so they would read a neighbour's sabotage and go red for it
# Two lanes in one sandbox is a false verdict in BOTH directions: a neighbour's sabotage reddens
# an innocent gate (which reports UNPROVABLE, "already red untampered" — a sentence that would be
# a lie), and a neighbour's restore can hand a gate CLEAN bytes at the exact moment it is supposed
# to be judging tampered ones, which reads as PROVEN. Grouping by tampered FILE does not fix it
# either: a gate reads far more than it tampers, which is what that 110 measures.
#
# So: ONE THROWAWAY SANDBOX PER LANE, gates pulled from a shared queue, every proof of a gate run
# serially inside the one lane that owns it. A lane is then EXACTLY the old serial loop over a
# subset of the gates; nothing is shared between lanes but the queue and the printer's lock. This
# changes WHEN work happens and never WHETHER: the same proofs run, in the same order within a
# gate, against the same bytes.
#
# ⚠ AND A LANE THAT DIES CANNOT CORRUPT ANYTHING. _prove_one restores in a `finally`, but a lane
# killed outright — the 10-minute foreground ceiling has killed pushes in this repo three times —
# leaves its sabotage inside a throwaway copy that no other lane and nothing in the real tree ever
# reads. The real tree is never written at all.
#
# DERIVATION OF THE DEFAULT, measured on his 10-core Mac, not estimated:
#   · one sandbox = safe_copy + the PROOF_NEEDS clones: 2.7s alone, 6.1s for 4 built at once,
#     ~384 MB of real disk each (1,534 MB for four, all of it reclaimed by rmtree)
#   · 4 lanes leave 6 cores for the gate subprocesses the lanes spend their time waiting on
#   · ⚠⚠ THE CEILING IS NOT THE CORE COUNT, IT IS THE GATES THAT ASSERT DURATIONS. test_control
#     takes 19.5s idle and 565.9s under concurrent load — a 29x slowdown that once produced a
#     FALSE RED and refused a legitimate push. Parallel proving MANUFACTURES exactly that load on
#     purpose, so the number stays low and can be turned DOWN without an edit.
# HEART2_PROVE_WORKERS=1 is the old single-sandbox behaviour, unchanged, for a loaded machine.
PROVE_WORKERS = 4
LANE_DISK_MB = 400            # measured ~384 MB of real disk per sandbox, rounded up
LANE_DISK_FLOOR_MB = 4096     # the same floor safe_copy itself refuses to copy below

# ══ AND THE DEADLINE HAS TO GROW WITH THE LOAD THE LANES THEMSELVES MANUFACTURE ═══════════════
# ⚠⚠ MEASURED, AND IT IS THE ONE THING THE A/B FOUND. Proving the same 25 gates (74 proofs) in a
# frozen copy of the tree, serial versus lanes:
#       serial 1 lane (cold 766.6s / warm 606.3s) · 2 lanes 286.3s · 4 lanes 258.4s
#       25 of 25 GATE verdicts identical at every lane count · 0 bytes of tree drift in all four
#       73 of 74 PROOF verdicts identical — and ONE flipped:
#           test_a_cached_absence_is_not_an_absence[0]  PROVEN -> UNPROVABLE
# It did not flip because a lane corrupted anything. Its CLEAN run takes ~110 s against a
# registered timeout of 120 s — measured at 230.3 s for clean+tampered in the SERIAL control, and
# that same control already reports its OTHER proof UNPROVABLE for the identical timeout reason.
# The gate sits on its own deadline, serially, on an idle machine. Any load at all tips it.
#
# ⚠ AND THE FLIP IS NOT HARMLESS. `UNPROVABLE` makes _write_state DISCARD a standing proof, so a
# deadline that expired because of MY concurrency would quietly delete a proof the heart had
# banked — a number walking backwards for a reason that is nothing to do with the law.
#
# The honest fix is not a smaller lane count: 2 lanes flips the SAME proof, measured. The deadline
# is an INSTRUMENT parameter — how long this prover waits before giving up — and it must not be
# what decides whether a law can be measured. So when more than one lane is running, every gate's
# registered timeout is multiplied by this. The number is measured, not guessed: the worst
# per-proof inflation observed at 4 lanes was 1.75x (1.2s -> 2.1s on a short gate, where fixed
# start-up contention dominates); long gates ran at 0.98x-1.01x. 2 covers that with margin.
# ⚠ IT APPLIES ONLY WHEN LANES > 1, so the single-lane path keeps the exact deadline it always
# had, and a genuinely hung gate still gives up — at 2x a bounded budget, never never.
LANE_DEADLINE_SCALE = 2
DEADLINE_SCALE = 1            # what _prove_one actually multiplies in; set by _prove_gates
#: REG-1997 - how many proving lanes run side by side right now (set by _prove_gates, 1 outside it). Every law run is told
#: (HEART2_LANES), so a law that judges its own CPU or wall cost can say the reading is the prover's load, not its code.
LANES_NOW = 1
#: ⚠⚠ #50 (REG-1454) — A BACKGROUND PROOF ON A SLOWER PC IS THE SAME CASE AS A BUSY LANE. On the ALT the
#: self-prove lane runs this at BELOW_NORMAL priority beside a console that is filming, and
#: `test_screen_parity` timed out at its 120 s on every proof - UNPROVABLE - while the same law passes in a
#: plain copy there given time. The deadline is this prover's patience, not the law, so the caller that
#: KNOWS it is running slow says so: heart2 reads HEART2_DEADLINE_SCALE (a number >= 1, capped at 8; junk
#: is ignored and said). A genuinely hung gate still gives up, at most 8x a bounded budget.
DEADLINE_SCALE_MAX = 8


def _deadline_scale(n_lanes, env=None, say=None):
    """The factor every gate's registered timeout is multiplied by in this run. -> int >= 1"""
    base = LANE_DEADLINE_SCALE if n_lanes > 1 else 1
    raw = (env if env is not None else os.environ).get("HEART2_DEADLINE_SCALE")
    if not raw:
        return base
    try:
        asked = int(float(raw))
    except (TypeError, ValueError):
        if say:
            say("  HEART2_DEADLINE_SCALE=%r is not a number - ignored" % raw)
        return base
    return max(base, min(DEADLINE_SCALE_MAX, max(1, asked)))


def prove_workers(n_gates=None, say=None):
    """How many lanes `--prove` may run at once. -> int >= 1

    ⚠ IT MUST BE TURNABLE DOWN WITHOUT AN EDIT, because the reason to turn it down is a machine
    that is already loaded — the condition under which editing a file and re-running is worst.
    An unreadable or absurd value falls back to the default AND SAYS SO: a number nobody asked
    for, chosen silently, is how a gate ends up measuring something else. [[unknown-stays-unknown]]

    ⚠ AND IT IS CAPPED BY FREE DISK, because each lane is a real copy. safe_copy refuses below
    4 GB free one copy at a time, but four lanes build CONCURRENTLY and that check would race.
    Answering 1 rather than 0 is deliberate: one lane is the old behaviour, and safe_copy still
    gets to refuse it honestly.
    """
    n = PROVE_WORKERS
    raw = os.environ.get("HEART2_PROVE_WORKERS")
    if raw is not None:
        try:
            n = int(str(raw).strip())
        except Exception:
            n = PROVE_WORKERS
            if say:
                say("  ⚠ HEART2_PROVE_WORKERS=%r is not a number — falling back to %d lane(s)"
                    % (raw, n))
        if n < 1:
            if say:
                say("  ⚠ HEART2_PROVE_WORKERS=%r is below 1 — using 1 lane (the serial loop)" % raw)
            n = 1
    n = max(1, min(int(n), 16))
    if n_gates:
        n = min(n, int(n_gates))
    try:
        import disk_room as _dr   # #151 (REG-2742) - purgeable space counts, as on every other floor
        free_mb = _dr.free_bytes(tempfile.gettempdir())[0] / (1024.0 * 1024.0)
        room = int((free_mb - LANE_DISK_FLOOR_MB) // LANE_DISK_MB)
        if room < n:
            if say:
                say("  ⚠ only %d MB free: %d lane(s) would leave less than %d MB, so this run uses "
                    "%d. Fewer lanes, never a skipped proof." % (int(free_mb), n,
                                                                 LANE_DISK_FLOOR_MB, max(1, room)))
            n = max(1, room)
    except Exception:
        pass
    return max(1, n)


#: REG-1683 (the v3544 eye) — a BUFFERED lane says it is alive at most this often, so the prover's log moves while a
#: gate's verdicts are still held. self_prove ends a prover whose log stands still past silent_bound_s, and that bound
#: assumes a line per proof - a multi-lane gate held every line until the WHOLE gate ended.
LANE_BEAT_EVERY_S = 60


class _LaneSay(object):
    """One lane's printer: it buffers, and flushes a whole gate's lines at once under a lock.

    ⚠ WITHOUT IT THE VERDICT LINES INTERLEAVE and the log stops being evidence — and the log is
    the only thing `--prove` produces. Flushed per gate rather than per run, so output still
    arrives while the proving is going on instead of all at the end.

    ⚠ AND WITH ONE LANE IT DOES NOT BUFFER AT ALL. HEART2_PROVE_WORKERS=1 is offered as "the old
    loop, unchanged", and a single lane that withheld its lines until a gate finished would not be
    that — a proof can take minutes, and somebody watching a stuck run needs the line for the proof
    it is stuck on. Nothing can interleave with itself, so there is nothing to buffer for.
    """

    def __init__(self, sink, lock, buffered=True, clock=None):
        self._buf, self._sink, self._lock, self._buffered = [], sink, lock, buffered
        self._clock, self._beat = clock or time.monotonic, None

    def __call__(self, *a):
        line = " ".join(str(x) for x in a)
        if not self._buffered:
            self._sink(line)
            return
        self._buf.append(line)
        # REG-1683 — ONE short line, straight through, at most every LANE_BEAT_EVERY_S: the gate's own lines stay
        # together (they flush at its end), and the log still moves, so a working prover never reads as a silent one.
        # A two-lane slice with one gate of three proofs at a scaled 480 s per run held its log 2,400 s against a
        # 2,040 s bound - ended mid-law, booked stalled, and the next slice repeated it.
        now = self._clock()
        if self._beat is None or now - self._beat >= LANE_BEAT_EVERY_S:
            self._beat = now
            with self._lock:
                self._sink("  · a proving lane is working - %d line(s) of its gate held until the gate ends"
                           % len(self._buf))

    def flush(self):
        if not self._buf:
            return
        buf, self._buf = self._buf, []
        with self._lock:
            for line in buf:
                self._sink(line)


# ══ #42 — PUSH TIME: PROVE EACH RED-PROOF WHERE ITS DEFECT SHOWS, LIKELIEST FAILURE FIRST, ONE BROWSER AT A TIME ════════
# His words, 2026-09-28: pushes take too long — "do #42 right after v3522 lands". MEASURED on the v3522 push: a lane
# takes a whole GATE and runs all its proofs back to back, so the character builder's width law (41 proofs, each a
# clean AND a tampered run of a law that renders ~33 viewports at ~100 s a run) was ONE ~105-minute thread, the mule
# window's (25 proofs) the other long pole, and the push gate took ~2h50m. Attempt 1 of that push ran 159 min and was
# refused on ONE blind proof that a targeted run finds in ~3 min. `--push` (hooks/pre-push passes it, nothing else
# does) changes three things, and without it not one line of the path below runs:
#   1. WHERE (P1): a proof that declares "widths" runs its clean AND its tampered run with TV_LAW_WIDTHS naming them
#      (tv/law_widths.py); a proof that declares none runs at every width, exactly as without --push - never skipped.
#      ⚠ FAIL CLOSED: a declared width at which the tamper stays green reads BLIND and the push refuses as it always
#      has - a wrong declaration can never read PROVEN. An UNPROVABLE at the declared widths is re-proved at EVERY
#      width and that verdict stands. run_gates and CI never set the variable: the full sweep stays the verdict of record.
#   2. WHEN (P2): the proofs likeliest to fail run FIRST - an anchor that no longer matches as declared, an entry new or
#      changed since the push base (@{push}, else origin/main - the hook's own order), a proof whose tampered file
#      changed - and the run STOPS at the first BLIND / INVALID / clean-run red, printed the moment it is found. Every
#      proof it did not reach is NOT RUN: never banked, never PROVEN, and the exit is non-zero - a stop is a refusal,
#      never a pass. With no failure every proof still runs.
#   3. ONE BROWSER AT A TIME: a gate that starts a browser (its import graph reaches render_check / playwright through
#      any number of helpers - browser_gates(), not pixel_gates()' one file - or it declares widths) holds ONE lock
#      while it is proved, whatever the lane count - four parallel Chrome lanes drove his Mac to load 100 on 2026-09-28.
#      Every other gate keeps its lane.
# The law: test_a_push_proof_runs_only_where_its_defect_shows. [[regression-guard]] [[unknown-stays-unknown]]
NOT_RUN = "NOT RUN"     # a push-time proof the run STOPPED before reaching - never a verdict, never banked
CLEAN = "CLEAN"         # REG-1992: a clean-only run came back green - the wave's answer, never a verdict, never banked
_PUSH = None            # the running push-time context (_PushRun) while prove(push=True) runs; None otherwise
# REG-1669 (#42) — ONE CLEAN RUN SERVES A GATE'S PROOFS. Every proof ran the untampered law first, so a gate with N
# proofs paid 2N runs where N+2 do: MEASURED on his ALT 2026-10-01, a 40-gate census slice took 82 minutes. While
# _prove_gate holds a gate, its lane thread keeps that gate's clean verdict here and every later proof reuses it; a
# CLOSING clean run after the last proof must still be green, or no PROVEN of the gate is kept (the sandbox did not
# stay clean across its proofs). Per thread, because lanes run gates side by side. None outside a gate: a direct
# _prove_one call still runs its own clean run, as it always has.
_CLEAN = threading.local()


#: REG-3212 - A PROOF CUT AT ITS BOUND. MEASURED on v3864 (ci/proof-keys-v3864, run 42061540765): shard 10 held 656 of
#: 8,829 proofs and proved from 16:17 until it was cancelled at 17:40 UTC - 87 min of job, every other shard done by 17:05 -
#: under a 160-minute step cap and a 180-minute job cap, while his max was 75; nothing fired. A CI run now bounds itself:
#: HEART2_GATE_CAP_S cuts one gate that has run past its cap, and
#: HEART2_PROVE_DEADLINE (epoch seconds) cuts every proof still to RUN once the run's own deadline has passed - so the
#: shard FINISHES, writes its manifest and uploads inside its job, instead of being killed with nothing written. A cut
#: proof is TIMEOUT: never PROVEN, never banked, never dropped - it is owed in the manifest (REG-2591's list), the fan-in
#: and the census name it, and Publish's verdict holds the deploy when it is one of the push's laws. A proof the cache
#: SERVES is still served past the bound (it runs nothing). Unset - his Mac's push, a PC's census - nothing is cut.
TIMEOUT = "TIMEOUT"


def _prove_bounds(env=None):
    """REG-3212 - (gate cap seconds | None, run deadline epoch seconds | None) from HEART2_GATE_CAP_S and
    HEART2_PROVE_DEADLINE. A value that is not a positive number is no bound (said by the run's seams line)."""
    env = os.environ if env is None else env
    out = []
    for k in ("HEART2_GATE_CAP_S", "HEART2_PROVE_DEADLINE"):
        try:
            v = float(str(env.get(k) or "").strip())
        except ValueError:
            v = None
        out.append(v if (v is not None and v > 0) else None)
    return out[0], out[1]


def _gate_cap_for(name, run_cap):
    """REG-3317 - this gate's cap: the run's HEART2_GATE_CAP_S, or a larger prove_cap_s its registration declares (its proofs
    measured past the run's cap). -> seconds | None. No run cap (his Mac's push, a PC's census): None - nothing is cut there."""
    if run_cap is None:
        return None
    try:
        import run_gates as _rg_cap
        for g in getattr(_rg_cap, "GATES", []):
            if getattr(g, "name", None) == name:
                own = getattr(g, "prove_cap_s", None)
                if isinstance(own, (int, float)) and own > run_cap:
                    return float(own)
                break
    except Exception:
        pass
    return run_cap


def _past_bound(run, gate_t0, now=None, cap=None):
    """REG-3212 - why a proof of a gate that started at `gate_t0` may no longer RUN, or None. -> str | None. Pure.
    `cap` is the gate's own cap (REG-3317, _gate_cap_for); None takes the run's."""
    now = time.time() if now is None else now
    dl = getattr(run, "deadline", None)
    cap = cap if cap is not None else getattr(run, "gate_cap", None)
    if dl is not None and now >= dl:
        return "the run's deadline passed %d s ago, so no proof still to run starts" % int(now - dl)
    if cap is not None and now - gate_t0 >= cap:
        return "this gate has run %d s, past its %d s cap" % (int(now - gate_t0), int(cap))
    return None


#: REG-3212 (the second eye on v3865) - THE BOUND CUTS A RUN ALREADY GOING, NOT ONLY THE NEXT ONE. MEASURED in the first
#: build: _past_bound was asked once, before each proof, and nothing killed a law run in flight - with 3 lanes the deadline
#: scale is 2, so a 900-s gate got 1800 s per run (its clean, tampered and closing runs up to 90 min), and a proof started
#: at minute 54 ran past the 70-minute step cap: the step was killed with no manifest, the fan-in refused the whole set.
#: Now every law run of a push takes the tighter of its own deadline and the bound: the run's HARD STOP (its deadline +
#: HARD_STOP_AFTER_S - in-flight runs get that long to finish, so the shard still writes its manifest and uploads inside
#: its job) and, for a gate's proofs, the gate's cap from its first proof. A run the bound killed is TIMEOUT, owed by name.
HARD_STOP_AFTER_S = 480
_BOUND = threading.local()          # REG-3212 - this lane's gate clock (t0: None outside a gate's proofs) and its last cut


def _hard_stop(run):
    """REG-3212 - when a law run still going is killed: the run's deadline + HARD_STOP_AFTER_S. -> epoch s | None"""
    dl = getattr(run, "deadline", None)
    return None if dl is None else dl + HARD_STOP_AFTER_S


def _inflight_limit(timeout, now=None, run=None, gate_t0=None):
    """REG-3212 - one law run's timeout under the push's bounds. -> (seconds, why | None). `why` is set only when a bound,
    not the law's own deadline, is the tighter one: the run is then TIMEOUT when it is killed, and seconds <= 0 means it
    may not start at all. No push, or no bound: (timeout, None) - his Mac's push and a PC's census are never cut."""
    run = _PUSH if run is None else run
    if run is None:
        return timeout, None
    now = time.time() if now is None else now
    best, why = None, None
    hs = _hard_stop(run)
    if hs is not None:
        best, why = hs - now, "the run's hard stop, %d s past its deadline" % HARD_STOP_AFTER_S
    t0 = getattr(_BOUND, "t0", None) if gate_t0 is None else gate_t0
    cap = (getattr(_BOUND, "cap", None) if t0 is not None else None) or getattr(run, "gate_cap", None)   # REG-3317
    if cap is not None and t0 is not None and (best is None or t0 + cap - now < best):
        best, why = t0 + cap - now, "this gate's %d s cap" % int(cap)
    if best is None or (timeout and timeout <= best):
        return timeout, None
    return max(0.0, best), why


def _served_here(cache, sandbox, name, filename, pr):
    """REG-3212 - would the verdict cache serve this proof (it runs nothing)? peek(), marking nothing. -> bool"""
    if cache is None:
        return False
    try:
        key = cache.key_for(sandbox, name, filename, pr)[0]
    except Exception:
        return False
    return key is not None and cache.peek(key) is not None


class _PushRun(object):
    """#42 — what the lanes of ONE `--prove --push` run share: the order, the browser lock, the stop."""

    def __init__(self, order=None, browser=(), cache=None, keep_going=False):
        self.order = dict(order or {})          # {gate: [proof index, ...]}, the likeliest to fail first
        # REG-2591 - a CI proof shard does not fail fast: one bad law stranded ~300 proofs of its shard (7 of 16 shards
        # at dcff7160). It records EVERY failure, skips only the failed gate's remaining proofs, and the shard stays red
        self.keep_going = bool(keep_going)
        self.failures = []                      # REG-2591: every (gate, index, verdict, reason), in the order found
        self.browser = set(browser or ())       # the gates proved one at a time: they start a browser
        self.browser_lock = threading.Lock()
        self.stop = threading.Event()
        self.first = None                       # (gate, index, verdict, reason): the failure that stopped the run
        self._lock = threading.Lock()
        self.cache = cache                      # P3: the verdict cache prove(push=True) opened, or None (every proof runs)
        self._items = None                      # REG-1989: the gates take() hands out, drained from the queue once
        self._qlock = threading.Lock()
        self.wave = False                       # REG-1992: True while the clean wave runs (one clean run per gate)
        self.clean_wave = {}                    # REG-1992: clean-run key -> (ok, tail) the wave measured
        self.proofs = {}                        # REG-2353: (gate, index) -> what the proof was forecast to do and did
        self.t0 = time.time()                   # REG-2353: the push record's clock
        self.sig0 = _SIGNAL_RUNS["n"]           # REG-2353: runs a signal ended before this run began
        self.wave_s = None                      # REG-2353: the clean wave's seconds, when one ran
        self.keys0 = _servable_keys(cache)      # REG-2353: every key the cache would serve when the run began
        self.direct = None                      # REG-2599: gates whose own law file the push changes (None: UNKNOWN)
        self.gate_cap, self.deadline = _prove_bounds()   # REG-3212: a gate's wall cap and the run's deadline (None: none)
        self.cut = []                           # REG-3212: every (gate, index) cut at its bound - TIMEOUT, owed, named
        self.ckpt = {"runs": 0, "s": 0.0, "banked": 0, "bankedS": 0.0, "red": 0, "revoked": 0,
                     "resumed": 0, "resumedS": 0.0}  # #150: checkpoint cost and what it bought, for the push record

    def fail(self, name, idx, verdict, reason):
        """Record a failure. Fail fast: the FIRST stops the run -> True for the call that stopped it. Keep going
        (REG-2591, a CI shard): every failure is recorded, nothing stops -> True (each is announced once)."""
        with self._lock:
            first = self.first is None
            if first:
                self.first = (name, idx, verdict, reason)
            self.failures.append((name, idx, verdict, reason))
        if self.keep_going:
            return True
        self.stop.set()
        return first

    def failed(self, name):
        """REG-2591 - has this gate already failed in this run (a red clean wave, say)? -> bool"""
        with self._lock:
            return any(f[0] == name for f in self.failures)

    def owe_line(self, name, idx, verdict, reason):
        """REG-2591 - what a kept-going shard says where a fail-fast run would say FAIL FAST. -> str"""
        return ("  ⚠ REG-2591 OWED — %s[%d] %s: %s. This shard KEEPS GOING: the gate's remaining proofs are NOT RUN, "
                "every other gate still runs, and the shard ends red with this one owed a fix." % (name, idx, verdict,
                                                                                                    reason))

    def browser_slot(self, name):
        """The lock a browser gate is proved under; for every other gate a context that holds nothing."""
        import contextlib
        return self.browser_lock if name in self.browser else contextlib.nullcontext()

    def take(self, work):
        """REG-1989 — the next gate for a lane, never one that parks it behind the browser while other work waits.
        -> ((name, filename, proofs), context the gate is proved under) | None when nothing is left

        MEASURED on the v3602 push (11 browser gates of 131): lanes took gates in queue order, and a lane that took a
        browser gate while another held the browser WAITED holding it - so the serial browser chain started late, ran
        last, and three lanes sat idle behind it for the tail. Now the free browser is always taken first (the serial
        chain is the critical path, so it starts at the run's first second and never stops while browser work is left),
        a lane that finds it busy takes the next gate that needs no browser, and only when nothing else is left does a
        lane wait for it. Each kind keeps its own fail-fast order. The lock is the same one; only who waits on it moved."""
        import contextlib
        with self._qlock:
            if self._items is None:
                self._items = []
                while True:
                    try:
                        self._items.append(work.get_nowait())
                    except Exception:
                        break
            if not self._items:
                return None
            if self.browser_lock.acquire(False):
                for k, it in enumerate(self._items):
                    if it[0] in self.browser:
                        return self._items.pop(k), _HeldLock(self.browser_lock)
                self.browser_lock.release()
            for k, it in enumerate(self._items):
                if it[0] not in self.browser:
                    return self._items.pop(k), contextlib.nullcontext()
            return self._items.pop(0), self.browser_lock     # only browser gates are left: wait for the one browser


def _servable_keys(cache):
    """REG-2353 — the keys a verdict cache would serve right now, asked of its side-effect-free peek() (lookup's own
    predicate). -> frozenset; empty with no cache. Never through lookup(): a serving read marks an entry USED, and this
    set is taken over every entry at push start, before one proof ran."""
    if cache is None:
        return frozenset()
    try:
        return frozenset(k for k in list(cache.entries) if cache.peek(k) is not None)  # SERVABLE-BY-PEEK
    except Exception:
        return frozenset()


#: REG-2353 (#42 R16) — the proof a push-time lane thread is proving right now: the path it was forecast to take (f: hit /
#: narrow / full, decided before any run of it), the path it took (a), its key and why it cannot be banked (u). Set only
#: around _prove_push_one by _prove_gate_push; every other caller's notes go nowhere.
_MARK = threading.local()


def _mark(once=False, **kw):
    """REG-2353 — note facts about the push-time proof this thread is proving. `once`: keep a value already noted."""
    m = getattr(_MARK, "m", None)
    if isinstance(m, dict):
        for k, v in kw.items():
            if not (once and k in m):
                m[k] = v


class _HeldLock(object):
    """REG-1989 — a lock take() already acquired for a gate: entering holds it, leaving releases it."""

    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.lock.release()
        return False


# ══ #42 P3 — THE VERDICT CACHE: A PROVEN IS REUSED ONLY OVER BYTE-IDENTICAL INPUTS ═════════════════════════════════
# MEASURED 2026-09-29 on the v3523 push: the render gate refused at minute 95 (twice), and every retry re-proved the
# same ~40 changed laws (~83 min) over a tree that had not changed by one byte - three times. His order, 2026-09-28:
# "this is CRITICAL we need to optimize clock time". So a push-time PROVEN is banked under a KEY that digests every byte
# the verdict can depend on, and the next push re-runs only the proofs whose key changed:
#   · the law file itself and every module it imports - TRANSITIVELY, by the same AST walk browser_gates() uses for the
#     one-browser lock (_imported_names): a helper the law reaches through two others is still what it runs;
#   · every file a literal string anywhere in that closure names (bible.html, control_ui.html, hooks/pre-push, a data
#     file). Over-inclusion is the only error this may make on purpose - a file named in an error message costs one
#     re-prove, never a stale PROVEN;
#   · the proof's tampered target - #41 rank 8: PROVEN was keyed to the GATE file alone (gates_fingerprint), so an edit
#     to the SUBJECT could make a proof BLIND while the census still read proven - and every PROOF_NEEDS that is a file;
#   · the proof entry itself (find / replace / matches / widths), the gate's registered spec (argv tail, -c script,
#     timeout) and the prover (this file, law_widths.py): a proof is only as true as the thing that produced it.
# ⚠ THE KEY IS TAKEN FROM THE SANDBOX, NOT THE REAL TREE. The sandbox is the exact tree the proof ran in (safe_copy of
#   the repo minus footage and .git), so a file the law names that is not in it was never read, and a target resolves
#   through the same resolve_proof_target the tamper uses. It is taken BEFORE the proof and AGAIN after: when the two
#   differ the tree moved under the proof and nothing is banked. The record carries repo-relative paths only.
# ⚠ UNKEYABLE IS NEVER CACHED. A closure module nobody can read or parse, a PROOF_NEEDS that is a directory (his footage,
#   .git), a target that is not a file inside the sandbox, a named file that cannot be read: the proof runs every push
#   and the line says why. A miss runs. Only PROVEN is ever stored - BLIND / INVALID / UNPROVABLE are findings, never
#   shortcuts - and only a stored PROVEN is ever reused, whatever else lands in the file.
# ⚠ ITS REACH, STATED: a file the law reaches by a COMPUTED path (an env var, a join of variables) is outside the key -
#   the same floor pixel_gates states for imports, one level down. A law about such a file names it in PROOF_NEEDS.
#   AND A LAW THAT LISTS A DIRECTORY ITSELF HAS AN INPUT NO BYTE KEY CAN NAME (second eye on the first cut): a law
#   calling os.listdir / os.walk / os.scandir / glob.glob / Path.glob / rglob / iterdir reads whatever is THERE at run
#   time - a law file added or removed between two pushes over otherwise identical bytes could turn it red - so such a
#   law is UNKEYABLE, said once, and runs every push (57 of 628 red-proof laws on 2026-09-29). The LAW FILE ONLY is
#   scanned: heart2, run_gates and control_app all list directories, and scanning the closure would make every heart
#   law unkeyable. A listing reached THROUGH the closure (gate_files() and the like) is outside the key - stated, not
#   solved; the anchors gate runs at every push regardless.
# ⚠ A REUSED PROOF KEEPS THE TIME IT WAS MEASURED. A hit is a verdict from an EARLIER run over the same bytes, so the
#   census stamps that gate with the OLDEST provedAt among its reused proofs (verdictAt), never this run's clock - the
#   first cut stamped every hit "now", the exact defect control_app's oldestProofMs was built against. [[stale-reading]]
#   A stored PROVEN with no readable provedAt is not reused: a verdict nobody can age cannot keep its age.
# ⚠ THE CACHE MAY COST A RE-PROVE, NEVER A VERDICT. Its own bookkeeping raising (a RecursionError from ast.parse on a
#   pathological module, a relpath across volumes, anything unforeseen) makes the proof unkeyable before the run and
#   "moved" after it; the verdict the run produced stands either way.
# ⚠ PUSH TIME ONLY. prove(push=True) - hooks/pre-push's `--prove NAMES --push` - is the only opener; _prove_push takes
#   the cache as a parameter and every other caller (the plain --prove path, run_gates, CI, a law driving _prove_push
#   with a fixture) hands none and runs every proof. The file is per machine, in git's common dir (REG-2340), never
#   committed and never copied into a sandbox. HEART2_PROVE_CACHE=0 leaves it closed for one run (the cold half of a
#   measurement) and says so.
# The law: test_a_proven_verdict_is_reused_only_on_identical_bytes. [[regression-guard]] [[unknown-stays-unknown]]
def _git_common_dir(repo):
    """R10 (REG-2340) - git's COMMON dir for the checkout at `repo`, read from the files git itself reads.
    -> (dir, None) | (None, why)

    Every worktree shape: a main checkout (.git is a directory); a linked worktree whose .git pointer names its gitdir by
    an absolute OR a relative path (worktree.useRelativePaths, git 2.48+) - relative to the CHECKOUT, never the cwd: the
    first cut normalised it against the cwd, so from anywhere but the checkout's own root it missed main; that gitdir's
    `commondir` file (git writes one for every linked worktree) names the common dir, so a worktree of a BARE repository
    resolves too; a submodule or a --separate-git-dir clone has no `commondir`, and its gitdir is its common dir. NEVER by
    running git: inside a hook GIT_DIR is inherited, and git would answer for whichever tree set it."""
    g = os.path.join(repo, ".git")
    try:
        if os.path.isdir(g):
            gitdir = g
        elif os.path.isfile(g):
            with io.open(g, encoding="utf-8") as fh:
                line = fh.read().strip()
            if not line.startswith("gitdir:"):
                return None, "its .git file is not a gitdir pointer"
            gitdir = line.split(":", 1)[1].strip()
            if not os.path.isabs(gitdir):
                gitdir = os.path.join(repo, gitdir)          # R10 - relative to the checkout, never the cwd
        else:
            return None, "it has no .git"
        gitdir = os.path.normpath(gitdir)
        if not os.path.isdir(gitdir):
            return None, "its .git pointer names %s, which is not a directory" % gitdir
        common = gitdir
        cd = os.path.join(gitdir, "commondir")
        if os.path.isfile(cd):
            with io.open(cd, encoding="utf-8") as fh:
                rel = fh.read().strip()
            common = os.path.normpath(rel if os.path.isabs(rel) else os.path.join(gitdir, rel))
        elif os.path.basename(os.path.dirname(gitdir)) == "worktrees":
            common = os.path.dirname(os.path.dirname(gitdir))  # git's own layout, when the commondir file is missing
        if not os.path.isdir(common):
            return None, "its common git dir %s is not a directory" % common
        return common, None
    except (OSError, ValueError) as _ge:
        return None, "its .git pointer could not be read (%s)" % type(_ge).__name__


def _shared_store(here=None, repo=None):
    """R10 (REG-2340) - WHERE heart2's per-machine stores live. -> (dir, None) | (this checkout's own dir, why)

    `<git common dir>/heart2/`: one per machine, shared by the main checkout and every worktree - where suite_verdict's
    store already lives. git never lists it, safe_copy never copies it (.git never travels), and code from before
    REG-2341 never opens it: that code keeps writing tv/.heart2_cache.json and tv/.heart2_red.json, so an old writer can
    never strip or shrink this store (the critic's rule). When no git dir can be found - a heart2 sandbox, a pointer that
    will not read - the stores are this checkout's own tv/.heart2_v2/, and `why` says so: they die with the checkout."""
    here = HERE if here is None else here
    repo = REPO if repo is None else repo
    common, why = _git_common_dir(repo)
    if common:
        return os.path.join(common, "heart2"), None
    return os.path.join(here, ".heart2_v2"), why


def _shared_cache_path(here=None, repo=None, env=None):
    """#242 (2026-10-07) - ONE VERDICT CACHE PER MACHINE, NOT ONE PER WORKTREE. -> the .heart2_cache.json to use

    MEASURED on the v3602 pushes: every pre-prove I ran in a worktree banked into THAT tree's cache, and the push in main
    read main's own - so the 136 laws the hook proved were proved from nothing while their worktree proofs sat unread
    one directory over. REG-2340: the cache is the one in _shared_store() - git's common dir, found from the checkout's
    .git without asking git. Sharing is safe for the same reason the cache is: an entry is reused only over
    byte-identical keyed inputs. What it cannot see - a law that reads live state by a computed path, present only in
    main - is why every entry records its TREE and the clean wave (REG-1992) skips only a gate whose proofs were banked
    in the tree being proved. HEART2_CACHE_PATH overrides (a law's seam)."""
    env = os.environ if env is None else env
    if env.get("HEART2_CACHE_PATH"):
        return env["HEART2_CACHE_PATH"]
    return os.path.join(_shared_store(here, repo)[0], ".heart2_cache.json")


#: #242 - the tree a verdict was proved in, carried on every banked entry (local only: the cache is never committed)
TREE_ID = os.path.realpath(REPO)
CACHE = _shared_cache_path()
#: R10 (REG-2340) - None when CACHE is the machine's shared store (or a seam named it); otherwise WHY it is this
#: checkout's own. The first opener of a store says it - a store that dies with its checkout is never silent.
CACHE_WHY = None if os.environ.get("HEART2_CACHE_PATH") else _shared_store()[1]
#: R4 (REG-2341) - entries kept, counted AFTER the merge with what is on disk (a trim before the merge was undone by
#: it, and the v1 file grew to 320 MB). With no per-entry inputs list an entry is about 0.3 KB.
CACHE_MAX = 50000
_NAME_MAX = 240           # a string constant longer than this is prose, not a path
#: the run's OWN records - written by the prove / render that reads them. Keyed, every law whose closure names heart2
#: (which names all of them) would miss on every push, and this cache would invalidate itself by being written. A record
#: of a run cannot make a tamper stay green, so these are the one named exclusion; every other named file is keyed.
_SELF_RECORDS = frozenset((".heart2.json", ".heart2_cache.json", ".heart2_cache.json.tmp", ".heart2_proposals.md",
                           ".render_verdict.json", ".heart2_red.json", ".heart2_red.json.tmp"))

# ══ R4 (REG-2341) — HEART2'S TWO STORES: LOCKED, MERGED, FSYNCED, A GOOD GENERATION KEPT, NEVER OVERWRITTEN UNREAD ════
# FOUND in the v1 writers (read 2026-10-21; main's cache measured 320 MB, 7,991 entries): each store had ONE fixed tmp
# name and no cross-process lock, so two provers (a worktree's pre-flight beside main's push) could tear or lose each
# other's write; a store that would not parse was read as empty and then OVERWRITTEN by the next write; and the cache's
# cap ran before the merge with the disk, which undid it - so the file only ever grew. Now every write of the verdict cache and of the red memory goes through
# ONE writer, _StoreFile.commit: an exclusive flock on the store's DIRECTORY across read-merge-write (a lock on the file
# would leave with the inode os.replace swaps out), a tmp named for this process and thread, fsync, the current file kept
# as `.prev`, then os.replace. A store that will not read is renamed aside (`.unreadable-<ms>`, the newest one kept) and
# its `.prev` merged in its place - never overwritten. Windows has no flock: there the lock is msvcrt's byte lock on ONE
# lock file in the store's directory (_LOCK_NAME), so both stores still share one lock per directory. A machine with
# neither writes unlocked and says so.
# TV_STORE_HOLD_S is a LAW's seam: it holds a written tmp unreplaced, so two writers provably overlap.
# The laws: test_two_provers_never_tear_the_store, test_an_unreadable_store_is_kept_not_overwritten.
try:
    import fcntl as _fcntl
except ImportError:                 # Windows: no flock - msvcrt's lock file stands in (_win_lock)
    _fcntl = None
try:
    import msvcrt as _msvcrt
except ImportError:                 # every machine but Windows
    _msvcrt = None
_RED_NAME = ".heart2_red.json"
#: R4 - Windows' stand-in for the directory flock: ONE empty lock file per store directory, shared by the cache and the
#: red memory as the flock is, its first byte held with msvcrt.locking. Named under the cache's own prefix, so no checkout
#: lists it (.gitignore tv/.heart2_cache*), no sandbox copies it (safe_copy's store prefixes), and the sweep of dead
#: writers' tmps never matches it. It is never deleted: a lock file removed while held is how two writers lock two files.
_LOCK_NAME = ".heart2_cache.lock"
_LOCK_WAIT_S = 300.0                # a Windows writer waits this long for the lock, then writes unlocked and says so
_STORE_SAID = set()


def _say_once(say, key, line):
    """A store's warning, once per process and key - a per-proof repeat would bury the verdict lines."""
    if key in _STORE_SAID:
        return
    _STORE_SAID.add(key)
    try:
        (say or print)(line)
    except Exception:
        pass


def _fsync(fd):
    """Push a file's (or a directory's) bytes to the disk: F_FULLFSYNC where the OS has it (macOS's fsync stops at the
    drive's cache), fsync otherwise. Best effort - the atomic rename is the guarantee, this is the durability."""
    try:
        if _fcntl is not None and hasattr(_fcntl, "F_FULLFSYNC"):
            _fcntl.fcntl(fd, _fcntl.F_FULLFSYNC)
            return
    except OSError:
        pass
    try:
        os.fsync(fd)
    except OSError:
        pass


def _store_hold():
    """TV_STORE_HOLD_S - a law's seam, never set by a push: hold a written tmp this long before it replaces the store."""
    try:
        s = float(os.environ.get("TV_STORE_HOLD_S") or 0)
    except ValueError:
        s = 0.0
    if s > 0:
        time.sleep(min(s, 30.0))


def _win_lock(folder):
    """R4 - Windows: an exclusive msvcrt lock on the first byte of `folder`'s lock file (_LOCK_NAME), polled with
    LK_NBLCK until it is free or _LOCK_WAIT_S has passed - then OSError, and the caller writes unlocked and says so.
    Each holder opens its own descriptor, and a Windows byte lock binds the handle that took it, so two threads exclude
    each other as two processes do. -> the lock file's fd, for _win_unlock"""
    fd = os.open(os.path.join(folder, _LOCK_NAME), os.O_RDWR | os.O_CREAT)
    deadline = time.time() + _LOCK_WAIT_S
    try:
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                _msvcrt.locking(fd, _msvcrt.LK_NBLCK, 1)
                return fd
            except OSError:
                if time.time() >= deadline:
                    raise
                time.sleep(0.05)
    except BaseException:
        os.close(fd)
        raise


def _win_unlock(fd):
    """Release _win_lock's byte and close its descriptor; the lock file itself stays (see _LOCK_NAME)."""
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
    except (OSError, ValueError):
        pass                                            # closing the descriptor releases it all the same
    finally:
        os.close(fd)


@contextlib.contextmanager
def _store_locked(folder, say=None):
    """R4 - an exclusive lock on `folder` (a store's directory) for the block, across processes and threads (each
    holder opens its own descriptor): flock on the directory itself; on Windows, which has no flock, msvcrt's byte lock
    on the directory's lock file (_win_lock). -> the directory's fd (fsync it after a rename), or None - on Windows,
    where no directory is opened, or when the write is unlocked (said)."""
    fd = win = None
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    if _fcntl is not None:
        try:
            fd = os.open(folder, os.O_RDONLY)
            _fcntl.flock(fd, _fcntl.LOCK_EX)
        except OSError as _le:
            if fd is not None:
                os.close(fd)
                fd = None
            _say_once(say, ("nolock", folder), "  ⚠ heart2 stores: %s could not be locked (%s) - this write is "
                                               "UNLOCKED" % (folder, type(_le).__name__))
    elif _msvcrt is not None:
        try:
            win = _win_lock(folder)
        except Exception as _le:
            _say_once(say, ("nolock", folder), "  ⚠ heart2 stores: %s could not be locked (%s) - this write is "
                                               "UNLOCKED" % (folder, type(_le).__name__))
    else:
        _say_once(say, ("nolock",), "  ⚠ heart2 stores: this machine has neither flock nor msvcrt, so a store write is "
                                    "merged but UNLOCKED - two writers at the same moment can still lose one write")
    try:
        yield fd
    finally:
        if fd is not None:
            try:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(fd)
        if win is not None:
            _win_unlock(win)


def _compact_inputs():
    """v3867 - a json object_hook that stores each entry's `inputs` ONCE: every path string interned, and entries whose
    input lists are equal share one list. -> hook(dict) -> dict. The bytes read and written do not change.

    MEASURED: his Mac's .heart2_cache.json is 320 MB holding 7,489,763 input paths in 8,007 entries - about 2,000
    distinct paths and 303 distinct lists. Loaded plain it is 1,392 MB resident; interned 702 MB; interned and shared
    334 MB. His work ALT (8 GB, the game beside it) imported v3865's 22 shards with 783 MB free and the commit at 13.0 of
    14.3 GB: 489 MB private, 15 MB of it resident, 19 proofs keyed a minute and a 9-hour ETA, every lock shut meanwhile.
    ⚠ A shared list is shared: nothing may change an entry's inputs in place - replace the list, never append to it
    (test_a_store_keeps_each_input_once pins that over tv/)."""
    shared = {}

    def hook(d):
        v = d.get("inputs")
        if type(v) is list and v:
            t = tuple(sys.intern(x) if type(x) is str else x for x in v)
            got = shared.get(t)
            if got is None:
                got = shared[t] = list(t)
            d["inputs"] = got
        return d
    return hook


def _read_store(path, valid=None):
    """-> (body, None); ({}, None) when the file is absent (nothing stored yet); (None, why) when it will not parse or
    `valid(body)` names what is wrong with it (without `valid`, anything but a JSON object is wrong)."""
    if not os.path.exists(path):
        return {}, None
    try:
        with io.open(path, encoding="utf-8") as fh:
            body = json.load(fh, object_hook=_compact_inputs())     # v3867 - each input stored once (see the hook)
    except Exception as _e:
        return None, "it would not parse (%s)" % type(_e).__name__
    bad = valid(body) if valid is not None else (None if isinstance(body, dict) else "it is not a JSON object")
    return (None, bad) if bad else (body, None)


def _entries_shape(body):
    """A v2 store keeps its records under 'entries'. -> why it is not one | None"""
    return None if isinstance(body, dict) and isinstance(body.get("entries"), dict) else "it has no 'entries' map"


def _num(x):
    """A store's stamp (at, usedAt) as a number; anything else is 0 - one corrupt entry must never raise inside a merge
    and so block every later write of the store."""
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else 0


def _set_aside(path, why, say=print):
    """R4 - an unreadable store is RENAMED, never overwritten: `<path>.unreadable-<ms>`, the newest one kept.
    -> True when it is out of the way (renamed, or already gone)"""
    folder, base = os.path.split(os.path.abspath(path))
    aside = "%s.unreadable-%d" % (path, int(time.time() * 1000))
    try:
        os.replace(path, aside)
    except FileNotFoundError:
        return True
    except OSError as _ae:
        say("  ⚠ %s is UNREADABLE (%s) and could not be set aside (%s) - nothing is written over it"
            % (base, why, type(_ae).__name__))
        return False
    try:
        for n in os.listdir(folder):
            if n.startswith(base + ".unreadable-") and n != os.path.basename(aside):
                os.remove(os.path.join(folder, n))      # keep ONE: the newest unreadable generation
    except OSError:
        pass
    say("  ⚠ %s was UNREADABLE (%s) - kept aside as %s, never overwritten" % (base, why, os.path.basename(aside)))
    return True


class _StoreFile(object):
    """R4 (REG-2341) - THE ONE WRITER of heart2's two per-machine stores, the verdict cache and the red memory."""

    def __init__(self, path, say=print, valid=_entries_shape):
        self.path, self.say, self.valid = path, say, valid

    def _tmp(self):
        return "%s.%d.%d.tmp" % (self.path, os.getpid(), threading.get_ident())

    def _merged(self, merge):
        """Read the store as it is NOW (under the lock) and hand it to merge(). An unreadable store is set aside and its
        last good generation (.prev) stands in. -> the body to write | None (nothing to write) | why (refused)"""
        disk, why = _read_store(self.path, self.valid)
        if why is not None:
            if not _set_aside(self.path, why, self.say):
                return "the unreadable store could not be set aside, so nothing is written over it"
            disk, pwhy = _read_store(self.path + ".prev", self.valid)
            self.say("  ⚠ heart2 store: %s" % ("its last good generation (.prev) is merged in its place"
                                               if pwhy is None and disk else "it has no readable .prev - what it held "
                                               "is in the file kept aside"))
            disk = disk if pwhy is None else None
        return merge(disk)

    def commit(self, merge):
        """Under the store directory's lock: merge(what is on disk now | None) -> the body, written atomically.
        -> (True, None) | (False, why | None)"""
        try:
            return self._commit(merge)
        except Exception as _ce:
            return False, "it could not be written (%s)" % type(_ce).__name__
        finally:
            for p in (self._tmp(), self._tmp() + ".prev"):
                if os.path.exists(p):
                    try:
                        os.remove(p)                    # this thread's tmp never outlives the write
                    except OSError:
                        pass

    def _commit(self, merge):
        # ⛔ IT NEVER EDITS A GUARD: the only files written are ones named like CACHE or the red memory - refused BEFORE
        # anything is read, set aside or created, and the guard sits right above the write the instruments law admits.
        if os.path.basename(self.path) != os.path.basename(CACHE) and os.path.basename(self.path) != _RED_NAME:
            return False, "refusing to write %s - heart2's stores are only named %s or %s" % (
                self.path, os.path.basename(CACHE), _RED_NAME)
        with _store_locked(os.path.dirname(os.path.abspath(self.path)), self.say) as lockfd:
            body = self._merged(merge)
            if not isinstance(body, dict):
                return False, body
            with io.open(self._tmp(), "w", encoding="utf-8") as fh:
                json.dump(body, fh, sort_keys=True)
                fh.flush()
                _fsync(fh.fileno())
            _store_hold()
            if os.path.exists(self.path):
                # the good generation being replaced stays one rename away (a hard link: no copy of the bytes)
                try:
                    os.link(self.path, self._tmp() + ".prev")
                    os.replace(self._tmp() + ".prev", self.path + ".prev")
                except OSError as _pe:
                    _say_once(self.say, ("noprev", self.path), "  ⚠ heart2 store: %s keeps no .prev generation (%s)"
                              % (os.path.basename(self.path), type(_pe).__name__))
            os.replace(self._tmp(), self.path)
            if lockfd is not None:
                _fsync(lockfd)                          # the rename itself reaches the disk
            return True, None

    def sweep(self):
        """R9 - tmps a DEAD writer left beside the store (its pid no longer runs) are removed; a live writer's never.
        -> how many (None: the store's folder could not be listed). Not on Windows, where asking a pid is not harmless
        (REG-1725)."""
        if os.name == "nt":
            return 0                                    # REG-1725: os.kill(pid, 0) is a Ctrl-C there, never a probe
        folder, base = os.path.split(os.path.abspath(self.path))
        if base not in (os.path.basename(CACHE), _RED_NAME):
            return 0                                    # only ever beside one of the two stores
        rx = re.compile(re.escape(base) + r"\.(\d+)\.\d+\.tmp(?:\.prev)?$")
        gone = 0
        try:
            names = os.listdir(folder)
        except FileNotFoundError:
            return 0                                    # no store folder yet: nothing was ever left in it
        except OSError:
            return None                                 # it could not be listed: UNKNOWN, never "none swept"
        for n in names:
            m = rx.match(n)
            if not m or int(m.group(1)) == os.getpid():
                continue
            try:
                os.kill(int(m.group(1)), 0)
                continue                                # alive, or not ours to judge: left alone
            except ProcessLookupError:
                pass
            except OSError:
                continue
            try:
                os.remove(os.path.join(folder, n))
                gone += 1
            except OSError:
                pass
        return gone

    _swept = set()                       # the store files this process has swept (sweep_once)

    def sweep_once(self):
        """R9 (Push A1) - sweep() at most once per process for this store file: the red memory has no open of its own
        (the verdict cache sweeps at every open), so before this nothing ever swept a dead writer's tmp beside it.
        -> how many removed (sweep's answer; 0 once this process has swept that file)"""
        p = os.path.abspath(self.path)
        if p in _StoreFile._swept:
            return 0
        _StoreFile._swept.add(p)
        return self.sweep()


# ══ #42 lever 1 (REG-1710) — THE RED MEMORY: A PROOF REMEMBERS WHICH CASES CAUGHT IT ══════════════════════════════════
# MEASURED 2026-10-02: pushes went from 17-20 minutes to 100+ because every batch touched tv/test_control.py, and each of
# its 6 sabotages re-ran ALL 2,259 cases (8-14 min apiece) to learn what one or two cases already said. Now, at push time,
# a tampered run that goes red writes down WHICH cases failed; the next push asks only those - untampered first (must be
# green), then tampered (must be red). Both hold -> PROVEN in seconds. Anything else - a renamed case, a subset that
# stays green, a run that cannot finish - falls back to today's FULL proof, so the memory can only ever save time, never
# grant a verdict the full proof would refuse.
#   HEART2_RED_MEMORY=0 closes it for one run (the cold half of a measurement).
# R2 (REG-2342) — ONE MEMORY PER MACHINE. MEASURED on the v3783 push (2026-10-21): it was per CHECKOUT, so the push from a
# fresh worktree ran test_control's 27 tampered proofs in full (187-227 s each, serial in the browser lock) while main's
# memory held proofs 0-26. It now lives beside the verdict cache (git's common dir, _shared_store); HEART2_RED_PATH names
# another file (a law's seam). It is keyed by the sabotage itself - gate, file, find, replace - with NO idx, so a proof
# inserted above another no longer re-keys every proof below it; a key from before R2 (with its idx) is still asked when
# the new one is unknown, and re-filed under the new key. It keeps 20,000 entries and evicts by USE, not by learning: a
# re-filed old key first, then an entry no gate file still declares, then the least recently used or learned. A push's
# first open folds every checkout's own pre-R2 tv/.heart2_red.json in (newest 'at' wins) and only READS them - older
# code keeps writing them. Its writes go through _StoreFile (locked, merged, never overwriting an unreadable memory).
# The law: test_a_proof_remembers_where_it_went_red. [[regression-guard]] [[unknown-stays-unknown]]
def _red_memory_path(cache=None, env=None):
    """R2 - the red memory: beside the verdict cache, unless HEART2_RED_PATH names another file. -> path"""
    env = os.environ if env is None else env
    if env.get("HEART2_RED_PATH"):
        return env["HEART2_RED_PATH"]
    return os.path.join(os.path.dirname(CACHE if cache is None else cache), _RED_NAME)


RED_MEMORY = _red_memory_path()
_RED_DEFAULT, _CACHE_DEFAULT = RED_MEMORY, CACHE     # the machine's own stores, as this process found them
RED_MEMORY_MAX = 20000     # entries kept, counted AFTER the merge; see _red_evict for who leaves first
RED_IDS_MAX = 60           # a sabotage that reddens more cases than this is asked in full anyway
_RED_ID_RX = re.compile(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)")
#: v3882 - an ANSI colour code (a coloured unittest header) is stripped before a red line is read
_ANSI_RX = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_RED_CASE_RX = re.compile(r"^[A-Za-z_]\w*\.test\w*$")
_RED_LOCK = threading.Lock()
_LAST_RED = {}             # thread id -> the red cases of that thread's last _run_gate (a side channel: stand-ins stay valid)
_RED = {"path": None, "sig": None, "entries": None, "folded": False}   # the memory as last read or written
_RED_USED = {}             # (memory file, key) -> [ms used, entry to re-file under the key | None, its pre-R2 key | None]


def _red_ids(lines):
    """The test cases a unittest run reported red. -> sorted ["Class.test_name", ...]

    Reads both shapes unittest prints - `FAIL: test_x (__main__.Class)` (3.9) and `(__main__.Class.test_x)` (3.11+).
    A class-level error (setUpClass, a module import) names no case a narrowed run could ask for, so it is dropped."""
    out = set()
    for ln in lines or ():
        m = _RED_ID_RX.match(_ANSI_RX.sub("", str(ln)).strip())   # v3882 - a coloured FAIL header is the same case
        if not m:
            continue
        test, where = m.group(1), m.group(2)
        if where.startswith("__main__."):
            where = where[len("__main__."):]
        if not test.startswith("test"):
            continue
        cid = where if where.endswith("." + test) else "%s.%s" % (where, test)
        if _RED_CASE_RX.match(cid):
            out.add(cid)
    return sorted(out)


class _RedKey(str):
    """A sabotage's identity (R2: no idx). `.legacy` is the key the same sabotage had before R2 - with its idx."""
    legacy = None


def _red_key(name, idx, pr):
    """One sabotage's identity: the gate and the exact bytes it tampers - NOT its place in the list (R2), so a proof
    inserted above it changes nothing. -> _RedKey (a str; .legacy = the pre-R2 key) | None"""
    try:
        f, fi, rp = str(pr.get("file") or ""), str(pr.get("find") or ""), str(pr.get("replace") or "")
        blob = json.dumps([str(name), f, fi, rp], ensure_ascii=False)
        key = _RedKey(hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24])
    except Exception:
        return None
    try:
        old = json.dumps([str(name), int(idx), f, fi, rp], ensure_ascii=False)
        key.legacy = hashlib.sha256(old.encode("utf-8")).hexdigest()[:24]
    except Exception:
        key.legacy = None
    return key


def _red_ids_of(e):
    """The case ids an entry remembers, only well-formed ones. -> [id] | None"""
    ids = e.get("ids") if isinstance(e, dict) else None
    ids = [str(i) for i in ids if _RED_CASE_RX.match(str(i))] if isinstance(ids, list) else []
    return ids[:RED_IDS_MAX] or None


def _red_load():
    """-> the memory's entries {key: entry}; {} when nothing is learned yet; None when it is closed
    (HEART2_RED_MEMORY=0). Read again only when its file changed (size, mtime, inode) - not once per proof. R9: this
    process's first read of a memory sweeps the tmps a dead writer left beside it."""
    if os.environ.get("HEART2_RED_MEMORY") == "0":
        return None
    with _RED_LOCK:
        _StoreFile(RED_MEMORY, print).sweep_once()   # R9 - a dead writer's tmp beside the red memory, once per process
        try:
            st = os.stat(RED_MEMORY)
            sig = (st.st_size, st.st_mtime_ns, st.st_ino)
        except OSError:
            sig = None
        if _RED["path"] == RED_MEMORY and _RED["sig"] == sig and _RED["entries"] is not None:
            return _RED["entries"]
        if RED_MEMORY == _RED_DEFAULT and CACHE_WHY and _is_prover_process():
            _say_once(print, ("red-own", RED_MEMORY), "  ⚠ the red memory is this checkout's own (%s) - what it learns "
                                                      "dies with the checkout" % CACHE_WHY)
        ent = {}
        if sig is not None:
            body, why = _read_store(RED_MEMORY, _entries_shape)
            if why is not None:
                # said, never silent: an unreadable memory costs this push its narrowed proofs, and the reason is in
                # the log. The next write sets it aside (never over it); until then its last good generation is asked.
                prev, pwhy = _read_store(RED_MEMORY + ".prev", _entries_shape)
                print("  ⚠ the red memory would not read (%s) - %s" % (
                    why, "its last good generation (.prev) is asked instead" if pwhy is None and prev
                    else "every proof runs in full this push"))
                body = prev if pwhy is None else None
            ent = (body or {}).get("entries") or {}
        _RED.update(path=RED_MEMORY, sig=sig, entries=ent)
        return ent


def _red_peek(key):
    """REG-2353 — the case ids that caught this sabotage before, read WITHOUT marking anything. -> [case id] | None

    The one read of the memory: the forecast asks it directly, and _red_recall - the push's own narrowing, the only
    reader that may mark an entry USED (R2 evicts by use) - answers with it. Asked through _red_recall, the forecast
    stamped every proof it forecast as used before a single one ran, and eviction by use kept nothing it meant. R2: when
    the key is unknown, the key the same sabotage had before R2 (with its idx) is asked."""
    d = _red_load()
    if not d or not key:
        return None
    ids = _red_ids_of(d.get(str(key)))
    if ids is None:
        old = getattr(key, "legacy", None)
        ids = _red_ids_of(d.get(old)) if old else None
    return ids


def _red_recall(key):
    """-> the case ids that caught this sabotage before (_red_peek's answer), or None: the push's narrowing (_prove_one).
    R2: every recall marks the entry USED - the memory evicts by use, never by when it learned - and a pre-R2 entry
    recalled by its old key is re-filed under the new key at the next write. The one place a recall may be marked
    USED - never the forecast, never the push record."""
    ids = _red_peek(key)
    if ids is None:
        return None
    d = _red_load() or {}
    k = str(key)
    old = None if _red_ids_of(d.get(k)) is not None else getattr(key, "legacy", None)
    e = d.get(old) if old else None
    with _RED_LOCK:
        _RED_USED[(RED_MEMORY, k)] = [int(time.time() * 1000), dict(e) if old else None, old]
    return ids


def _red_remember(key, name, idx, ids):
    if not key or not ids or len(ids) > RED_IDS_MAX:
        return
    now = int(time.time() * 1000)
    _red_write({str(key): {"gate": str(name), "proof": int(idx), "ids": list(ids), "at": now, "usedAt": now}})


def _red_merged(disk, learned, used):
    """R2 - what is on disk, plus what this process learned and used: newest 'at' wins a key, usedAt is the latest
    anyone recorded, and a recalled pre-R2 entry lands under its new key (the old one is marked, so it leaves first).
    -> {key: entry}"""
    out = dict((k, v) for k, v in (disk or {}).items() if isinstance(v, dict))

    def put(k, e):
        cur = out.get(k)
        if cur is None or _num(e.get("at")) > _num(cur.get("at")):
            if cur is not None and _num(cur.get("usedAt")) > _num(e.get("usedAt")):
                e = dict(e, usedAt=cur["usedAt"])
            out[k] = e
        elif _num(e.get("usedAt")) > _num(cur.get("usedAt")):
            out[k] = dict(cur, usedAt=e["usedAt"])

    for k, e in (learned or {}).items():
        if isinstance(e, dict):
            put(k, e)
    for k, (ms, refile, old) in (used or {}).items():
        if isinstance(refile, dict) and k not in out:
            out[k] = dict(((a, b) for a, b in refile.items() if a not in ("v1", "refiled")), usedAt=ms)
            if old in out:
                out[old] = dict(out[old], refiled=k)
        elif k in out and _num(out[k].get("usedAt")) < ms:
            out[k] = dict(out[k], usedAt=ms)
    return out


def merge_red_files(files, out, say=print):
    """v3891 (#194, his 11-09: "make sure it keeps getting faster self improve it") - THE RED MEMORY TRAVELS WITH THE SEED.
    Each CI shard starts on a fresh runner, so its red memory (beside its own cache) was always EMPTY: every round re-ran
    every test_control sabotage over all 2,259 cases (~270 s a proof - the costliest single chunk, the round's floor),
    though the last round had written down which cases caught each one. The fan-in merges every shard's memory with this
    module's own rules (_red_merged: newest 'at' wins a key; _red_evict: the 20,000 cap) into the next seed, and every
    shard starts from it. The memory only ever saves time (#42 lever 1: the narrowed pair must be green untampered and red
    tampered, else the full proof runs), so carrying it can never grant a verdict the full proof would refuse.
    files: the shards' .heart2_red.json; out: the seed's copy. -> 0 always (a memory that cannot travel costs time only)"""
    ent, read = {}, 0
    for f in files or []:
        body, why = _read_store(f, _entries_shape)
        if why is not None:
            say("  v3891 (#194) RED MEMORY: %s would not read (%s) - left out" % (os.path.basename(os.path.dirname(f)), why))
            continue
        ent = _red_merged(ent, (body or {}).get("entries"), None)
        read += 1
    if not read:
        say("  v3891 (#194) RED MEMORY: no shard left one - the next round starts empty")
        return 0
    gone = _red_evict(ent, RED_MEMORY_MAX)
    body = {"_why": "#42 lever 1 / R2 / v3891 #194 - which cases caught each sabotage, merged from a round's shards for the "
                    "next round's seed. Written only by tv/heart2.py.", "format": 2, "entries": ent}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with io.open(out + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        os.replace(out + ".tmp", out)
        say("  v3891 (#194) RED MEMORY: %d shard memor(ies) merged - %d sabotage(s) remembered%s, carried to the next seed"
            % (read, len(ent), (", %d evicted at the cap" % gone) if gone else ""))
    except OSError as e:
        say("  v3891 (#194) RED MEMORY: the merged memory could not be written (%s) - the next round starts empty"
            % type(e).__name__)
    return 0


def _red_live_keys():
    """Every key a gate file still declares - its R2 key and its pre-R2 key. -> set | None (UNKNOWN: that tier is
    skipped, never guessed)"""
    try:
        out = set()
        for name, fn in gate_files(say=lambda *a, **k: None):
            for i, pr in enumerate(red_proofs_in(fn) or []):
                k = _red_key(name, i, pr) if isinstance(pr, dict) else None
                if k:
                    out.add(str(k))
                    if k.legacy:
                        out.add(k.legacy)
        return out or None
    except Exception:
        return None


def _red_evict(ent, cap, live=None):
    """R2 - over the cap, AFTER the merge, these leave first: a pre-R2 key already re-filed under its new one, then an
    entry no gate file still declares, then the one least recently USED or learned. -> how many left"""
    over = len(ent) - cap
    if over <= 0:
        return 0
    live = _red_live_keys() if live is None else live

    def rank(k):
        e = ent[k] if isinstance(ent[k], dict) else {}
        return (0 if e.get("refiled") else 1,
                0 if (live is not None and k not in live) else 1,
                max(_num(e.get("at")), _num(e.get("usedAt"))))

    for k in sorted(ent, key=rank)[:over]:
        ent.pop(k, None)
    return over


def _red_write(learned=None):
    """R2/R4 - the red memory's ONE write: what is on disk now, plus what this process learned, used and re-filed,
    capped AFTER the merge. A memory that cannot be written costs the next push time, never a verdict. -> bool"""
    if os.environ.get("HEART2_RED_MEMORY") == "0":
        return False
    with _RED_LOCK:
        mine = [pk for pk in _RED_USED if pk[0] == RED_MEMORY]       # uses recorded against THIS memory file only
        used = dict((pk[1], _RED_USED[pk]) for pk in mine)
        if not learned and not used:
            return False
        out = {}

        def merge(disk):
            ent = _red_merged((disk or {}).get("entries"), learned, used)
            _red_evict(ent, RED_MEMORY_MAX)
            body = dict((k, v) for k, v in (disk or {}).items() if k not in ("_why", "format", "entries"))
            body.update(_why="#42 lever 1 / R2 - which cases caught each sabotage, per machine; keyed by gate, file, "
                             "find and replace. Written only by tv/heart2.py's _StoreFile.", format=2, entries=ent)
            out["entries"] = ent
            return body

        ok, why = _StoreFile(RED_MEMORY, print).commit(merge)
        if ok:
            for pk in mine:
                _RED_USED.pop(pk, None)
            try:
                st = os.stat(RED_MEMORY)
                _RED.update(path=RED_MEMORY, sig=(st.st_size, st.st_mtime_ns, st.st_ino), entries=out["entries"])
            except OSError:
                _RED.update(path=None, sig=None, entries=None)
        elif why:
            _say_once(print, ("red-write", RED_MEMORY, why), "  ⚠ the red memory was not written (%s) - the next push "
                                                             "asks those proofs in full" % why)
        return ok


def _red_flush():
    """The uses and re-files this process recorded, written - on the verdict cache's per-gate beat and at exit."""
    if _RED_USED:
        try:
            _red_write(None)
        except Exception:
            pass


atexit.register(_red_flush)


def _red_v1_sources(repo=None):
    """R2 - the per-checkout memories of the old layout: this checkout's, the main checkout's and every live worktree's
    tv/.heart2_red.json, found through git's common dir (<common>/worktrees/*/gitdir). -> [existing path]"""
    repo = REPO if repo is None else repo
    found = [os.path.join(repo, "tv", _RED_NAME)]
    common, _cw = _git_common_dir(repo)
    if common:
        if os.path.basename(common) == ".git":
            found.append(os.path.join(os.path.dirname(common), "tv", _RED_NAME))
        wt = os.path.join(common, "worktrees")
        try:
            names = sorted(os.listdir(wt))
        except FileNotFoundError:
            names = []                                  # no linked worktree was ever made in this repository
        except OSError as _le:
            print("  ⚠ the worktree list could not be read (%s) - no worktree's pre-R2 red memory is folded in"
                  % type(_le).__name__)
            names = []
        for n in names:
            try:
                with io.open(os.path.join(wt, n, "gitdir"), encoding="utf-8") as fh:
                    p = fh.read().strip()
            except (OSError, ValueError):
                continue                                # a half-made or pruned worktree record: nothing to read
            if p:
                p = p if os.path.isabs(p) else os.path.join(wt, n, p)
                found.append(os.path.join(os.path.dirname(os.path.normpath(p)), "tv", _RED_NAME))
    out, seen = [], set()
    for p in found:
        r = os.path.realpath(p)
        if r not in seen and os.path.isfile(p):
            seen.add(r)
            out.append(p)
    return out


def _red_fold(sources, say=print):
    """R2 - fold pre-R2 memories (flat {key: entry} files) into this machine's: an entry keeps its key (it holds its
    idx; recall falls back to it and re-files it), newest 'at' wins, and the old files are only READ. -> entries taken"""
    got = {}
    for p in sources or ():
        d, why = _read_store(p)
        if why is not None:
            _say_once(say, ("red-v1", p), "  ⚠ a pre-R2 red memory would not read (%s) - left as it is: %s" % (why, p))
            continue
        for k, e in d.items():
            if _red_ids_of(e) and _num(e.get("at")):
                if k not in got or e["at"] > _num(got[k].get("at")):
                    got[k] = dict(e, v1=1)
    if not got:
        return 0
    have = _red_load() or {}
    fresh = dict((k, e) for k, e in got.items()
                 if not isinstance(have.get(k), dict) or e["at"] > _num(have[k].get("at")))
    if fresh and _red_write(fresh):
        say("  #42 lever 1 (R2): %d sabotage(s) learned in a checkout's own pre-R2 memory now serve this machine"
            % len(fresh))
        return len(fresh)
    return 0


def _is_prover_process():
    """Is this process heart2's own CLI (the hook's `heart2.py --prove ... --push`), not a law driving it in-process?"""
    return os.path.basename(str(sys.argv[0] if sys.argv else "")) == "heart2.py"


def _red_fold_checkouts(say=print):
    """R2 - at a push's first open: every checkout's own pre-R2 memory folded into the machine's, once per process. Only
    in the prover's own process and only into the machine's OWN memory: a law that drives prove(push=True) in-process,
    a law's fixture store, or a seam never folds his checkouts' memories anywhere."""
    if _RED["folded"] or os.environ.get("HEART2_RED_MEMORY") == "0":
        return 0
    _RED["folded"] = True
    if not _is_prover_process():
        return 0
    if (os.environ.get("HEART2_RED_PATH") or os.environ.get("HEART2_CACHE_PATH") or RED_MEMORY != _RED_DEFAULT
            or CACHE != _CACHE_DEFAULT):
        return 0
    try:
        return _red_fold(_red_v1_sources(), say)
    except Exception as _fe:
        say("  ⚠ the checkouts' pre-R2 red memories could not be folded in (%s) - left as they are" % type(_fe).__name__)
        return 0


def _prove_narrow(sandbox, label, tgt, tgt_rel, find, repl, want, filename, timeout, w, ids, widths, say):
    """#42 lever 1 — ONE proof, asked only of the cases that caught it before. -> PROVEN | None (decide in full)

    Untampered, those cases must be GREEN (a renamed case, a red case or a run that cannot finish answers None); tampered,
    they must be RED. Only that pair is a proof. Every other outcome returns None and the full proof decides - so a
    BLIND law can never be called PROVEN here: its tampered subset stays green and the full run says BLIND."""
    t0 = time.time()
    args = list(ids)
    ok_c, _tc = _run_gate(sandbox, filename, timeout=timeout, extra=args, script=None, **w)
    if ok_c is not True:
        return None
    try:
        with io.open(tgt, encoding="utf-8") as fh:
            _orig = fh.read()
    except Exception:
        return None
    got = _orig.count(find) if find else 0
    if got < 1 or (want is not None and got != want):
        return None
    tampered = _orig.replace(find, repl) if want is None else _orig.replace(find, repl, want)
    if tgt_rel.endswith(".py"):
        try:
            ast.parse(tampered)
        except SyntaxError:
            return None
    with io.open(tgt, "w", encoding="utf-8") as fh:
        fh.write(tampered)
    try:
        ok_t, _tt = _run_gate(sandbox, filename, timeout=timeout, extra=args, script=None, **w)
    finally:
        with io.open(tgt, "w", encoding="utf-8") as fh:
            fh.write(_orig)
    if ok_t is False:
        say("     %-52s %s (%d match(es) tampered → red in the %d case(s) that caught it before, %.0f s)%s"
            % (label, PROVEN, got, len(ids), time.time() - t0, _at_widths(widths)))
        return PROVEN
    return None


def lf_normalised_bytes(data):
    """The bytes a proof key digests, on both the machine that proved and the machine that takes.

    The ALT checks text out with core.autocrlf=true (CRLF). The Mac leaves autocrlf unset (LF).
    Those are one commit. A NUL means the file is not text git converts, so its bytes stay as stored:
    normalising a binary would forge a key. A lone CR is a different byte and still differs."""
    if not isinstance(data, (bytes, bytearray)) or b"\0" in data or b"\r\n" not in data:
        return data
    return data.replace(b"\r\n", b"\n")


def _sha_file(path, memo=None):
    """sha256 of a file's LF-normalised bytes -> hex | None (unreadable).

    The bytes are always read. A same-size rewrite can keep the same mtime_ns on a filesystem
    whose timestamps do not move, and a memo keyed only on (path, size, mtime_ns) then serves the
    hash from before the rewrite. `memo` still records the digest for this run after the read.
    Text is LF-normalised first (lf_normalised_bytes), so a Windows checkout and a Mac checkout of
    the same commit key alike. A binary is hashed as stored."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    k = (path, st.st_size, st.st_mtime_ns)
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    data = lf_normalised_bytes(data)
    h.update(data)
    d = h.hexdigest()
    if memo is not None:
        memo[k] = d
    return d


def _sha_quiet(path, memo):
    """REG-2631 - _sha_file, served from `memo` while no _prove_one has started or ended since it was read. -> hex | None"""
    try:
        st = os.stat(path)
    except OSError:
        return None
    gen = _QUIET["gen"]
    k = ("REG-2631", path, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino, gen)
    d = memo.get(k)
    if d is None:
        d = _sha_file(path)
        if d is not None and _QUIET["gen"] == gen:
            memo[k] = d
    return d


def _inside(root, path):
    try:
        return os.path.commonpath([os.path.realpath(root), os.path.realpath(path)]) == os.path.realpath(root)
    except Exception:
        return False


def _named_files(tree, sandbox, repo):
    """The existing FILES the string constants of one parsed module name, relative to tv/ or the repo root. -> set
    An absolute constant is skipped: it points outside the sandbox (Chrome's binary, a home path) - the environment,
    not the tree - and a constant that climbs out of the repo is skipped for the same reason."""
    out = set()
    for x in ast.walk(tree):
        if not (isinstance(x, ast.Constant) and isinstance(x.value, str)):
            continue
        s = x.value
        if not s or len(s) > _NAME_MAX or "\n" in s or "\x00" in s or os.path.isabs(s):
            continue
        if os.path.basename(s) in _SELF_RECORDS:
            continue
        for base in (sandbox, repo):
            p = os.path.normpath(os.path.join(base, s))
            if os.path.isfile(p) and _inside(repo, p):   # one stat first: most constants name no file (5x, v3847)
                out.add(p)
    return out


#: the calls that LIST A DIRECTORY, by the module that owns them. The receiver decides, never the bare name:
#: `ast.walk` is a walk over a syntax tree and 195 laws call it (measured 2026-09-29); `os.walk` lists a directory.
_LISTS_OS = frozenset(("listdir", "scandir", "walk"))
_LISTS_GLOB = frozenset(("glob", "iglob"))
_LISTS_PATH = frozenset(("glob", "rglob", "iterdir"))     # pathlib's, on any receiver that is not a module alias


def _lists_a_directory(tree):
    """The FIRST call in `tree` that lists a directory -> ("os.listdir", line) | None.

    Reads the module's own imports so `import glob as _g; _g.glob(...)` and `from os import listdir` count and a
    helper that happens to be named `walk` does not. Over-inclusion (a method named `glob` on some other object)
    costs one re-prove per push, never a stale PROVEN - the only error this may make on purpose. Its reach: a
    directory listed through a subprocess (`ls`, `find`, `git ls-files`) is outside it."""
    mods, froms = {"os": "os", "glob": "glob"}, {}
    for x in ast.walk(tree):
        if isinstance(x, ast.Import):
            for a in x.names:
                if a.name in ("os", "glob"):
                    mods[a.asname or a.name] = a.name
        elif isinstance(x, ast.ImportFrom) and x.module in ("os", "glob"):
            for a in x.names:
                froms[a.asname or a.name] = (x.module, a.name)
    hits = []
    for x in ast.walk(tree):
        if not isinstance(x, ast.Call):
            continue
        f = x.func
        if isinstance(f, ast.Attribute):
            recv = mods.get(f.value.id) if isinstance(f.value, ast.Name) else None
            if (recv == "os" and f.attr in _LISTS_OS) or (recv == "glob" and f.attr in _LISTS_GLOB):
                hits.append(("%s.%s" % (recv, f.attr), x.lineno))
            elif recv is None and f.attr in _LISTS_PATH:
                hits.append(("%s()" % f.attr, x.lineno))
        elif isinstance(f, ast.Name) and f.id in froms:
            m, n = froms[f.id]
            if (m == "os" and n in _LISTS_OS) or (m == "glob" and n in _LISTS_GLOB):
                hits.append(("%s.%s" % (m, n), x.lineno))
    return min(hits, key=lambda h: h[1]) if hits else None


def _tracked_files(repo=None):
    """#242 (2026-10-08, his order: "preserving the proves" · "optimizing exactly this to save wall clock time" · "this is
    it critical") - the repo-relative paths git TRACKS in the real tree, once per call site. -> frozenset | None (UNKNOWN)

    MEASURED on the v3618 push: the wrapper pre-proved and BANKED 66 proofs on the final bytes, and the hook ten minutes
    later reused ONE of them. test_vault_population's key held 1,144 inputs, and among them 40+ runtime files his live
    console rewrites every few seconds (.subscription_budget.json 2 s old, shadow_watch.json 4 s, board_*.json 10 s): a
    literal like "board_tally.json" anywhere in control_app's closure makes that file a key input, so every key moved
    between any two pushes and the cache could never hit. Such a file is DATA no law may read (fixtures never touch live
    data); the named-file half of the key counts only files git tracks. The closure, the tampered target, PROOF_NEEDS and
    the prover are unchanged. None (git not answering) leaves the key as it was - over-inclusion, never a stale PROVEN."""
    repo = REPO if repo is None else repo
    try:
        import git_quiet as _gq
        r = _gq.run(["git", "-C", repo, "ls-files", "-z"], capture_output=True, timeout=30, env=_git_free_env())
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return frozenset(x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x)


def law_inputs(sandbox, filename, proofs, parsed=None, tracked=None, allow_listing=False, skip_modules=(),
               closure=None):
    """#42 P3 — every file in `sandbox` (a copied tv/) that a law's verdict can depend on. -> (sorted [abs path], why)

    `why` is None when every input could be found and read; otherwise the reason this law is UNKEYABLE (the list then
    holds what was found before that reason, for the line that says so). The closure walk is browser_gates()'s: the
    law, every tv/ or repo-root module it imports, and so on. Each proof's tampered target and every PROOF_NEEDS file
    join it; a PROOF_NEEDS directory makes the law unkeyable (his footage and .git are never hashed).
    `parsed` (one run) memoises each module's imports and named files on (path, size, mtime_ns): control_app.py is in
    most closures and costs ~1 s to walk, and a target the tamper rewrote and restored is walked again, never served
    from before the tamper."""
    repo = os.path.dirname(os.path.abspath(sandbox))
    law = os.path.normpath(os.path.join(sandbox, filename))
    if not os.path.isfile(law):
        return [], "the gate file is not in the sandbox"
    local = {}
    for d in (repo, sandbox):                      # tv/ listed last, so a tv/ module wins over a root one
        try:
            for f in os.listdir(d):
                if f.endswith(".py"):
                    local[f[:-3]] = os.path.join(d, f)
        except OSError:
            return [], "the sandbox could not be listed, so what this law imports is UNKNOWN"
    inputs, seen, stack = set(), set(), [law]
    while stack:
        p = os.path.normpath(stack.pop())
        if p in seen:
            continue
        seen.add(p)
        try:
            st = os.stat(p)
            mk = (p, st.st_size, st.st_mtime_ns)
        except OSError:
            mk = None
        if parsed is not None and mk is not None and mk in parsed:
            names, named, lists = parsed[mk]
        else:
            src = _read_text(p)
            if src is None:
                return sorted(inputs), "%s cannot be read" % os.path.relpath(p, repo)
            try:
                tree = ast.parse(src)
            except (SyntaxError, ValueError):
                return sorted(inputs), "%s will not parse" % os.path.relpath(p, repo)
            names, named, lists = _imported_names(tree), _named_files(tree, sandbox, repo), _lists_a_directory(tree)
            if parsed is not None and mk is not None:
                parsed[mk] = (names, named, lists)
        # the floor: a law that lists a directory ITSELF reads what is there at run time - no byte key can name that.
        # Only the law file is asked (the closure lists directories everywhere; see the block comment above).
        if p == law and lists and not allow_listing:
            return sorted(inputs), ("the law lists a directory itself (%s at line %d) - what it reads is decided at "
                                    "run time, so no byte key can name it" % lists)
        inputs.add(p)
        if closure is not None:           # REG-2640 - the modules the AST walk imports, never dropped by the trace
            closure.add(p)
        for dep in names & set(local):
            # A module the caller named is not walked from a dependency. The law file's own
            # import still is: that is the gate reading it, not an inherited one.
            if dep in skip_modules and p != law:  # LEDGER-SKIP-RUNNER
                continue
            stack.append(local[dep])
        if tracked is not None:           # #242 (2026-10-08) - a named file git does not track is runtime data, not a key input
            named = {q for q in named if os.path.relpath(q, repo).replace(os.sep, "/") in tracked}
        inputs |= named
    for pr in (proofs or []):
        rel = str(pr.get("file") or "") if isinstance(pr, dict) else ""
        if not rel:
            return sorted(inputs), "a proof names no file"
        tgt = os.path.normpath(resolve_proof_target(sandbox, rel))
        if not (_inside(repo, tgt) and os.path.isfile(tgt)):
            return sorted(inputs), "the tampered target %r is not a file inside the sandbox" % rel
        inputs.add(tgt)
    needs = proof_needs_in(law)
    if needs is None:
        return sorted(inputs), "its PROOF_NEEDS cannot be read"
    for need in needs:
        s = os.path.normpath(os.path.join(sandbox, need))
        if os.path.isdir(s):
            return sorted(inputs), "PROOF_NEEDS %r is a directory - his footage and .git are never hashed" % need
        if os.path.isfile(s):
            inputs.add(s)
        # absent: the sandbox never brought it, so the gate reads UNPROVABLE there and this proof is never PROVEN
    # REG-3319 - the trace that decides what a key may drop is part of the prover: its node half (node_trace.cjs) is a
    # byte input of every key beside heart2.py, so a change to what the hook sees re-proves every narrowed proof
    for prover in ("heart2.py", "law_widths.py", os.path.join("gate_trace", "node_trace.cjs")):
        p = os.path.join(sandbox, prover)
        if os.path.isfile(p):
            inputs.add(p)
    return sorted(inputs), None


def _load_cache(path):
    """-> (entries, None) | (None, why). An absent file is an EMPTY cache; a file that will not parse or has the wrong
    shape is UNREADABLE - said, never read as empty. R4: the next write sets it aside - it is never written over."""
    body, why = _read_store(path, _entries_shape)
    if why is not None:
        return None, why
    return (body or {}).get("entries") or {}, None


def _proven_at(e):
    """An entry's provedAt as a number, or -1 when it has none a reader could date."""
    t = e.get("provedAt") if isinstance(e, dict) else None
    return t if isinstance(t, (int, float)) and not isinstance(t, bool) else -1


def _compact_entry(entry):
    """R4 (REG-2341) - an entry keeps HOW MANY inputs it was keyed on and a digest of their names, never the list: the
    lists were nearly all of the 320 MB v1 file, and the key already digests every byte. -> the entry (a copy if changed)"""
    if not (isinstance(entry, dict) and isinstance(entry.get("inputs"), list)):
        return entry
    names = [str(p) for p in entry["inputs"]]
    out = dict((k, v) for k, v in entry.items() if k != "inputs")
    out["nInputs"] = len(names)
    out["inputsDigest"] = hashlib.sha256("\0".join(names).encode("utf-8", "replace")).hexdigest()[:16]
    return out


def _merged_cache(disk, mine, used):
    """R4 - what is on disk NOW, plus what this run holds and used: for one key the newer proof (provedAt) wins and
    usedAt is the latest anyone recorded. Nothing is trimmed here - the cap runs after this. -> {key: entry}"""
    out = dict((k, v) for k, v in (disk or {}).items() if isinstance(v, dict))
    for k, e in (mine or {}).items():
        if not isinstance(e, dict):
            continue
        d = out.get(k)
        if d is None or _proven_at(e) >= _proven_at(d):
            if d is not None and _num(d.get("usedAt")) > _num(e.get("usedAt")):
                e = dict(e, usedAt=d["usedAt"])
            out[k] = e
        elif _num(e.get("usedAt")) > _num(d.get("usedAt")):
            out[k] = dict(d, usedAt=e["usedAt"])
    for k, ms in (used or {}).items():
        if isinstance(out.get(k), dict) and _num(out[k].get("usedAt")) < ms:
            out[k] = dict(out[k], usedAt=ms)
    return out


def _live_gate_names():
    """The gate names this checkout still registers. -> set | None (UNKNOWN: that eviction tier is skipped)"""
    try:
        return set(n for n, _f in gate_files(say=lambda *a, **k: None)) or None
    except Exception:
        return None


def _cache_evict(ent, cap, live=None):
    """R4 - over the cap, AFTER the merge, these leave first: an entry no reader could serve (not PROVEN, or undated),
    then one SUPERSEDED by a newer proof of the same gate, proof, target and widths, then one whose gate is no longer
    registered, then the least recently used or proved. -> how many left"""
    over = len(ent) - cap
    if over <= 0:
        return 0
    newest = {}
    for k, e in ent.items():
        if e.get("verdict") == PROVEN and _proven_at(e) >= 0:
            ident = (e.get("gate"), e.get("proof"), e.get("target"), e.get("at"), e.get("why"))
            if ident not in newest or _proven_at(e) > _proven_at(ent[newest[ident]]):
                newest[ident] = k
    live = _live_gate_names() if live is None else live

    def rank(k):
        e = ent[k]
        if not (e.get("verdict") == PROVEN and _proven_at(e) >= 0):
            return (0, 0)
        if newest.get((e.get("gate"), e.get("proof"), e.get("target"), e.get("at"), e.get("why"))) != k:
            return (1, _proven_at(e))
        if live is not None and e.get("gate") not in live:
            return (2, _proven_at(e))
        return (3, max(_proven_at(e), _num(e.get("usedAt"))))

    for k in sorted(ent, key=rank)[:over]:
        ent.pop(k, None)
    return over


#: REG-3193 - "ask git for this set" (the default); an import worker is handed its parent's answer, None (UNKNOWN) too
_ASK_GIT = object()


class _VerdictCache(object):
    """#42 P3 — the PROVEN verdicts one machine may reuse at push time, and the counts a run prints beside them."""

    def __init__(self, path=None, say=print, tracked=_ASK_GIT, kept=_ASK_GIT):
        self.path = path or CACHE
        self.say = say
        self.lock = threading.Lock()
        self.memo = {}                   # (path, size, mtime_ns) -> sha256, this run only
        self.parsed = {}                 # (path, size, mtime_ns) -> (imports, named files), this run only
        # REG-3193 - an import worker is handed its parent's two answers (None, UNKNOWN, included) and asks git nothing
        self.tracked = _tracked_files() if tracked is _ASK_GIT else tracked  # #242 (2026-10-08) - the named files a key may count: tracked ones only
        self.kept = _kept_files() if kept is _ASK_GIT else kept              # REG-2944 - untracked and not ignored: a listed dir's entries beside the tracked
        self.traced = {"banked": 0, "refused": 0, "why": {}}   # REG-2944 - listing laws, this run, for the push record
        self.closures = {}               # (sandbox, filename) -> (inputs, why): one closure walk per law per lane
        self.rels = {}                   # v3883 - (path, repo) -> repo-relative "/" name: pure, no file state
        self.hits = self.misses = self.stores = self.unkeyable = self.moved = 0
        self.carried, self.carried_by = 0, {}       # REG-3046 - hits whose PROVEN another PC earned (carried)
        self.dirty = False               # stores since the last flush - written per GATE, not per proof
        self._said = set()               # (gate, why): an unkeyable law's reason is said once, not once per proof
        self.reused = {}                 # (gate, proof) -> provedAt ms of the entry a hit served, this run
        self.measured = {}               # gate -> the OLDEST provedAt among its reused proofs; the census stamp
        self.used = {}                   # R4 - key -> ms of this run's hits (usedAt), written at the next flush
        self.dropped = {}                # #150 - key -> provedAt this run REVOKED: the flush removes it from disk too
        self._vidx, self._vgen = None, None   # REG-2640 - ident -> unread-sets, rebuilt when the entries are replaced
        self.seed = {}                   # REG-2961 - a CI shard's earlier proofs, read only: seed_from()
        self.file = _StoreFile(self.path, say)
        self.file.sweep()                # R9 - a tmp a dead writer left beside the store
        if self.path == CACHE and CACHE_WHY:
            say("  #42 P3 CACHE: the machine's shared store was not found (%s) - this checkout's own is used, and what it "
                "banks dies with the checkout" % CACHE_WHY)
        ent, why = _load_cache(self.path)
        self.readable = why is None
        prev = _load_cache(self.path + ".prev")[0] if why and os.path.exists(self.path + ".prev") else None
        if not self.readable:
            say("  #42 P3 CACHE: %s is UNREADABLE (%s) - it is set aside at the first write, never written over; %s"
                % (os.path.basename(self.path), why, "its last good generation (.prev, %d entr(ies)) stands in"
                   % len(prev) if prev is not None else "no readable .prev, so every proof runs"))
        self.entries = ent if ent is not None else (prev if prev is not None else {})

    def lists(self, sandbox, filename):
        """REG-2944 - does this law FILE list a directory itself (the static rule's question)? -> bool"""
        ck = ("REG-2944 lists", sandbox, filename)
        with self.lock:
            if ck in self.closures:
                return self.closures[ck]
        src = _read_text(os.path.join(sandbox, filename))
        try:
            got = bool(src is not None and _lists_a_directory(ast.parse(src)))
        except (SyntaxError, ValueError):
            got = False
        with self.lock:
            self.closures[ck] = got
        return got

    def ignored_in(self, repo, rel_dir):
        """REG-2944 - the gitignored entry names of a listed directory (neither tracked nor kept). -> set | None"""
        if self.tracked is None or self.kept is None:
            return None
        d = os.path.join(repo, *[x for x in rel_dir.split("/") if x and x != "."])
        try:
            names = os.listdir(d)
        except OSError:
            return set()
        pre = "" if rel_dir in ("", ".") else rel_dir.rstrip("/") + "/"
        return set(n for n in names if not self._kept_entry(pre + n))

    def _kept_entry(self, rel):
        """REG-2944 - is this path, or anything under it, tracked or kept (never runtime data)? -> bool"""
        if rel in self.tracked or rel in self.kept:
            return True
        with self.lock:
            dirs = self.closures.get("REG-2944 dirs")
            if dirs is None:
                dirs = set()
                for q in set(self.tracked or ()) | set(self.kept or ()):
                    parts = q.split("/")
                    for i in range(1, len(parts)):
                        dirs.add("/".join(parts[:i]))
                self.closures["REG-2944 dirs"] = dirs
        return rel in dirs

    def _listing_material(self, repo, listed):
        """REG-2944 - for each listed dir: its tracked / kept entries, sorted, each with its kind and a file's bytes. ->
        (bytes, None) | (None, why). An absent directory is material too ("absent"): one appearing is a new key."""
        if self.tracked is None or self.kept is None:
            return None, "git could not say which files are tracked, so a listing cannot be keyed"
        h = hashlib.sha256(b"REG-2944 listing\0")
        for rel in sorted(listed):
            d = os.path.join(repo, *[x for x in rel.split("/") if x and x != "."])
            h.update(rel.encode("utf-8", "replace") + b"\0")
            if not os.path.isdir(d):
                h.update(b"absent\0")
                continue
            pre = "" if rel in ("", ".") else rel.rstrip("/") + "/"
            for n in sorted(os.listdir(d)):
                q = pre + n
                if not self._kept_entry(q):
                    continue                          # runtime data (#242): never key material
                full = os.path.join(d, n)
                if os.path.islink(full):
                    kind = "l:" + os.readlink(full)
                elif os.path.isdir(full):
                    kind = "d"
                else:
                    kind = _sha_quiet(full, self.memo)
                    if kind is None:
                        return None, "%s cannot be read" % q
                h.update(n.encode("utf-8", "replace") + b"\0" + kind.encode("utf-8", "replace") + b"\0")
        return h.hexdigest().encode("ascii"), None

    def key_for(self, sandbox, name, filename, pr, unread=None, listed=None, pre=None):
        """-> (key | None, [repo-relative inputs], why-unkeyable | None), from the SANDBOX's bytes now.

        REG-2640: `unread` None asks for the key a reader should look up - the byte-for-byte v1 key, or, when no PROVEN
        is servable under it, the first v2 key (a recorded unread-set of this same proof) that is. A list keys exactly
        those inputs by name only (v2; [] is v1): the key a traced PROVEN is banked under.
        REG-3193 - `pre` {(unread, listed): _key's answer} holds what an import worker computed from these same bytes
        (_key_job); a call it does not hold is computed here. Only _shard_keyer passes it."""
        def _k(un, ls):
            got = pre.get((tuple(un), ls)) if pre else None
            return got if got is not None else self._key(sandbox, name, filename, pr, un, ls)
        if unread is None:
            k1, rels, why = _k((), None)
            if k1 is None or self.peek(k1) is not None:
                return k1, rels, why
            for un, ls in self._variants(self.ident(name, filename, pr)):
                if not set(un) <= set(rels):
                    continue
                k2, rels2, why2 = _k(un, ls)
                if k2 is not None and self.peek(k2) is not None:
                    return k2, rels2, why2
            return k1, rels, why
        return self._key(sandbox, name, filename, pr, tuple(unread), listed)

    def ident(self, name, filename, pr):
        """REG-2640 - which proof an entry is, across trees: its law file, its declaration, its gate's spec."""
        return hashlib.sha256(json.dumps([str(filename), _proof_key(pr), gate_spec(name)], sort_keys=True,
                                         default=str).encode("utf-8", "replace")).hexdigest()[:32]

    def _variants(self, ident):
        """REG-2640 - the unread-sets banked for one proof, newest first (at most 8). -> [(unread rels, listed | None)]
        REG-2944 - and the listed-sets: a listing law's entry carries the directories its traced runs listed."""
        with self.lock:
            if self._vidx is None or self._vgen != id(self.entries):
                idx = {}
                for e in list(self.entries.values()) + list(self.seed.values()):   # REG-2961 - a seeded v2 key too
                    if not (isinstance(e, dict) and e.get("ident")):
                        continue
                    un = e.get("unread") if isinstance(e.get("unread"), list) else []
                    ls = tuple(str(x) for x in e["listed"]) if isinstance(e.get("listed"), list) else None   # REG-2944
                    if un or ls is not None:
                        idx.setdefault(e["ident"], []).append((_proven_at(e), (tuple(str(x) for x in un), ls)))
                self._vidx, self._vgen = idx, id(self.entries)
            got = sorted(self._vidx.get(ident, ()), reverse=True)
        out = []
        for _t, un in got:
            if un not in out:
                out.append(un)
        return out[:8]

    def _key(self, sandbox, name, filename, pr, unread, listed=None):
        repo = os.path.dirname(os.path.abspath(sandbox))
        with self.lock:
            ck = (sandbox, filename)
            if ck not in self.closures:          # REG-2944 - a listing law is walked too; its key waits for its trace
                self.closures[ck] = law_inputs(sandbox, filename, [], parsed=self.parsed, tracked=self.tracked,
                                               allow_listing="traced")
            base, why = self.closures[ck]
        if why:
            return None, [], why
        # the closure is shared by every proof of the law (walked once per lane); the target is this proof's own,
        # resolved exactly as _prove_one resolves it before tampering
        rel = str(pr.get("file") or "") if isinstance(pr, dict) else ""
        if not rel:
            return None, [], "the proof names no file"
        tgt = os.path.normpath(resolve_proof_target(sandbox, rel))
        if not (_inside(repo, tgt) and os.path.isfile(tgt)):
            return None, [], "the tampered target %r is not a file inside the sandbox" % rel
        inputs = sorted(set(base) | {tgt})
        # REG-2602 - the stamp lines leave this key only for a law that never reads the version, in a coherent tree
        GL = _ledger()
        stamped = [p for p in inputs if self._rel(p, repo) in GL.STAMP_SURFACES]
        mask, lits = False, None
        if stamped:
            law = os.path.join(sandbox, filename)
            # v3883 - served within a quiet stretch (REG-2631's rule, the one every other input already keys by): the four
            # stamp surfaces - bible.html is 8.9 MB - were read whole on EVERY key, and an import asks up to 9 keys an entry
            surf = tuple(_sha_quiet(os.path.join(repo, *r.split("/")), self.memo) for r in sorted(GL._STAMP_REQUIRED))
            law_sha = _sha_quiet(law, self.memo)
            vk, rk = ("REG-2602 version", repo) + surf, ("REG-2602 reads", sandbox, filename, law_sha)
            if vk not in self.closures:            # keyed on the surfaces' bytes: a one-file edit mid-run is seen
                self.closures[vk] = _tree_version(repo)
            if rk not in self.closures:
                reads = _law_reads_version(name, law, self._imported(base))
                got = None
                if not reads:
                    try:
                        with open(law, encoding="utf-8", errors="replace") as fh:
                            got = GL.script_literals(fh.read())
                    except OSError:
                        got = None
                self.closures[rk] = (reads or got is None, got)
            ver = self.closures[vk]
            reads, lits = self.closures[rk]
            pk = _proof_key(pr)
            mask = (ver is not None and not reads and not GL._VERSION_WORDS.search(pk)
                    and not _PROOF_VERSIONISH.search(pk))
            if mask:
                inputs = sorted(set(inputs) | {os.path.join(sandbox, "gate_ledger.py"), os.path.join(sandbox, "stamp_leak.py")})
        unread = frozenset(unread or ())
        if unread and not unread <= set(self._rel(p, repo) for p in inputs):
            return None, [], "REG-2640: an unread input is not among this proof's inputs"
        lists = self.lists(sandbox, filename)
        if not lists:
            listed = None                             # a law that does not list keeps its v1 / v2 key byte for byte
        lmat = None
        if lists:
            if listed is None:
                # REG-2944 - BEFORE the run nothing says what it will list: a pending key no entry is ever stored under,
                # taken again after the run (a static input that moved is still a tree that moved under the proof)
                h = hashlib.sha256(b"heart2 P3 key pending-listing\0")
            else:
                lmat, lwhy = self._listing_material(repo, listed)
                if lmat is None:
                    return None, [], lwhy
                h = hashlib.sha256(b"heart2 P3 key v3\0")
        else:
            h = hashlib.sha256(b"heart2 P3 key v2\0" if unread else b"heart2 P3 key v1\0")
        h.update(str(filename).encode("utf-8", "replace") + b"\0")
        h.update(_proof_key(pr).encode("utf-8", "replace") + b"\0")
        h.update(json.dumps(gate_spec(name), sort_keys=True, default=str).encode("utf-8", "replace") + b"\0")
        rels, away = [], []
        for p in inputs:
            rel = self._rel(p, repo)
            if rel in unread:                         # REG-2640 - no traced run opened it: its name, never its bytes
                d = "unread" if os.path.isfile(p) else None
            elif mask and rel in GL.STAMP_SURFACES:
                d, gone = self._masked_sha(p, rel)
                away.append((rel, gone or ""))
            else:
                d = _sha_quiet(p, self.memo)          # REG-2631 - outside the lock, served within a quiet stretch
            if d is None:
                return None, [], "%s cannot be read" % rel
            h.update(rel.encode("utf-8", "replace") + b"\0" + d.encode("ascii") + b"\0")
            rels.append(rel)
        if mask:   # the law's own literals, counted in what the mask took away
            for rel, gone in away:   # per surface: a word moving from one file's stamp to another's is a move
                h.update(b"REG-2602 literals\0" + rel.encode("utf-8", "replace") + b"\0"
                         + json.dumps(_literal_counts(lits, gone), ensure_ascii=True).encode("ascii") + b"\0")
        if lmat is not None:                          # REG-2944 - what every listed directory held, names and bytes
            h.update(b"REG-2944 listed\0" + lmat + b"\0")
        if lists and listed is None:
            return "pending-listing:" + h.hexdigest(), rels, None
        return h.hexdigest(), rels, None

    def _imported(self, paths):
        """Every module name an import in `paths` (one closure) names, from the walk's memo. -> set. A .py the walk never
        parsed is a file some module only NAMES (run_gates names tv/windows_boot_check.py in a description), not one
        this law imports; one another law's walk parsed adds its imports too - more readers, never fewer."""
        out = set()
        for p in paths:
            if not p.endswith(".py"):
                continue
            try:
                st = os.stat(p)
                got = self.parsed.get((os.path.normpath(p), st.st_size, st.st_mtime_ns))
            except OSError:
                got = None
            if got is not None:
                out |= set(got[0])
        return out

    def _rel(self, p, repo):
        """v3883 - os.path.relpath(p, repo) with "/" separators, memoised (pure: two strings in, one out). MEASURED on the
        work ALT 11-08: 110,150 relpath calls were 40% of the keyer's time - every input of every key, again per variant."""
        k = (p, repo)
        r = self.rels.get(k)
        if r is None:
            r = self.rels[k] = os.path.relpath(p, repo).replace(os.sep, "/")
        return r

    def _masked_sha(self, path, rel):
        """REG-2602 - ('m:' + sha256 of the file's bytes with its stamp lines masked, the masked-away text) | (None, None).
        The digest never equals a raw one, so a masked key and a raw key cannot meet.
        v3883 - served within a quiet stretch (REG-2631: the same file identity and no _prove_one started or ended since it
        was read) - it read and hashed the whole surface on every key, bible.html's 8.9 MB included."""
        try:
            st = os.stat(path)
            qk = ("REG-2602q", path, rel, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino, _QUIET["gen"])
        except OSError:
            qk = None
        if qk is not None:
            with self.lock:
                if qk in self.memo:
                    return self.memo[qk]
        gen = _QUIET["gen"]
        got = self._masked_sha_read(path, rel)
        if qk is not None and got[0] is not None and _QUIET["gen"] == gen:
            with self.lock:
                self.memo[qk] = got
        return got

    def _masked_sha_read(self, path, rel):
        """REG-2602 - _masked_sha's read: the bytes are always read here; only the masking is memoised, on them."""
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return None, None
        data = lf_normalised_bytes(data)
        raw = hashlib.sha256(data).hexdigest()   # the bytes are always read; only the masking is memoised, on them
        with self.lock:
            if ("REG-2602", rel, raw) in self.memo:
                return self.memo[("REG-2602", rel, raw)]
        m = _stamp_masked(rel, data)
        d = (None, None) if m is None else ("m:" + hashlib.sha256(m[0]).hexdigest(), m[1])
        with self.lock:
            self.memo[("REG-2602", rel, raw)] = d
        return d

    def count(self, what):
        with self.lock:
            setattr(self, what, getattr(self, what) + 1)

    def say_once(self, name, why, line):
        with self.lock:
            first = (name, why) not in self._said
            self._said.add((name, why))
        if first:
            self.say(line)

    def reused_at(self, name, idx, ms):
        """Record that proof `idx` of `name` was served from an entry measured at `ms` (epoch ms)."""
        with self.lock:
            self.reused[(name, idx)] = ms

    def peek(self, key):
        """REG-2353 — the entry lookup() would serve for `key`, with NO side effect. -> the PROVEN entry | None

        THE ONE PREDICATE a banked verdict passes to be reused: lookup() answers with it, and lookup() is the only reader
        that marks an entry USED (R4's usedAt: the store evicts by use). The push record's servable set and the forecast
        ask peek(): through lookup() they stamped EVERY entry as used at push start, before one proof ran, and eviction
        by use kept nothing it meant. Only a PROVEN that carries a readable provedAt is a shortcut; a verdict nobody can
        date cannot keep its age in the census, so it is re-proved."""
        with self.lock:
            e = self.entries.get(key)
            if e is None:
                e = self.seed.get(key)       # REG-2961 - an earlier run's proof, under the key these bytes give it
        if not (isinstance(e, dict) and isinstance(e.get("provedAt"), (int, float))
                and not isinstance(e.get("provedAt"), bool)):
            return None
        # R4 (critic) - MISSING OR UNREADABLE FACTS ARE A MISS, ALWAYS: an entry that stands on facts (a traced kind, a
        # facts reference) is served only by a reader that checks those facts - never by this byte key, never as "none"
        if e.get("kind", "static") != "static" or "facts" in e or "factsRef" in e:
            return None
        return e if isinstance(e, dict) and e.get("verdict") == PROVEN else None

    def lookup(self, key):
        """The stored entry for `key` when it may be served (peek's answer, exactly); anything else in the file is not
        a shortcut. The serving read: a hit here is a proof the push reuses, and the only read that may mark it used
        (R4, track T1: its usedAt mark goes HERE, between the answer and the return - never inside peek())."""
        e = self.peek(key)  # LOOKUP-ASKS-PEEK
        if e is not None:
            with self.lock:
                self.used[key] = int(time.time() * 1000)       # R4 - usedAt: eviction is by use, written at the flush
                if key not in self.entries:                   # REG-2961 - served from the seed: this run's own now
                    self.entries[key] = e
                    self.dirty = True
                    self._vidx = None
        return e

    def seed_from(self, path):
        """REG-2961 (#161 stage 2) - A CI SHARD SERVES WHAT AN EARLIER RUN PROVED OVER THE SAME BYTES. The shard's own file
        still starts empty (REG-2585); `path` (HEART2_SHARD_SEED: the proofs the last main run banked, restored by
        actions/cache) is read ONLY, into self.seed. peek() asks it after self.entries and serves an entry only under the
        key key_for() takes from THIS checkout's bytes - the key is a sha256 over every input's bytes (_key), so a seed
        entry for other bytes is never found, whatever cache the restore handed over. An entry served from it is copied
        into this run's entries (lookup), so the shard's file holds only proofs of its own plan: served or proved here.
        -> (entries seeded, why-unread | None)"""
        body, why = _read_store(path, _entries_shape)
        if why is not None:
            return 0, why
        with self.lock:
            self.seed = dict((k, v) for k, v in ((body or {}).get("entries") or {}).items() if isinstance(v, dict))
            self._vidx = None
        return len(self.seed), None

    def store(self, key, entry):
        """Bank one PROVEN in memory; flush() writes the file (once per gate, and at the end of the run). R4: nothing is
        trimmed here - the cap runs after the merge with the disk, which undid every trim made before it."""
        with self.lock:
            self.entries[key] = _compact_entry(entry)
            self.dirty = True
            self._vidx = None                 # REG-2640 - a new unread-set is servable at once

    def unstore(self, key, proved_at):
        """#150 (REG-2942) - revoke a PROVEN this run banked, because a LATER clean run of its gate went red. Only an
        entry no newer than the one banked is taken back (another run's newer proof of the same bytes stands). -> bool"""
        with self.lock:
            e = self.entries.get(key)
            gone = isinstance(e, dict) and _proven_at(e) <= proved_at
            if gone:
                self.entries.pop(key, None)
            self.dropped[key] = proved_at
            self.dirty = True
            self._vidx = None
            return gone

    def flush(self):
        """Write what this run banked and used, merged with what is on disk NOW and capped after that merge, through
        the stores' one locked writer. -> True when written. R2: the red memory's recorded uses ride the same per-gate
        beat (its own file, its own write)."""
        try:
            return self._flush()
        finally:
            _red_flush()

    def _flush(self):
        with self.lock:
            if not (self.dirty or self.used):
                return False
            mine, used, out, dropped = dict(self.entries), dict(self.used), {}, dict(self.dropped)

            def merge(disk):
                # #242 - ONE FILE, SEVERAL PROVERS: what another run banked since this one loaded is kept - R4 reads it
                # under the lock, so no write lands between this read and this write
                ent = _merged_cache((disk or {}).get("entries"), mine, used)
                out["evicted"] = _cache_evict(ent, CACHE_MAX)
                for _dk, _dms in dropped.items():           # #150 - a revoked proof leaves the disk, never a newer one
                    if isinstance(ent.get(_dk), dict) and _proven_at(ent[_dk]) <= _dms:
                        ent.pop(_dk, None)
                body = dict((k, v) for k, v in (disk or {}).items() if k not in ("_why", "format", "entries"))
                body.update(_why="#42 P3 - PROVEN verdicts this machine may reuse at push time, keyed by a digest of "
                                 "every byte each depends on (tv/heart2.py law_inputs). Per machine, never committed. "
                                 "R4: format 2, no inputs lists, written only by tv/heart2.py's _StoreFile.",
                            format=2, entries=ent)
                out["entries"] = ent
                return body

            ok, why = self.file.commit(merge)
            if ok:
                self.entries, self.used = out["entries"], {}
                self.dropped = {}
                self.readable, self.dirty = True, False
                return True
            # a cache that cannot be written costs the next push a re-prove, never this push its verdict - said
            self.say("  #42 P3 CACHE: %s" % (why if str(why).startswith("refusing") else
                                             "could not write %s (%s) - what this run proved is not banked"
                                             % (os.path.basename(self.path), why)))
            return False

    def summary(self, n_total):
        _by = ", ".join("%s %d" % kv for kv in sorted(self.carried_by.items()))
        return ("#42 P3 CACHE: %d of %d proof(s) reused from the cache (byte-identical inputs, not re-run; %d of them "
                "carried from another PC%s) · %d proved and banked · %d missed and re-proved · %d not cacheable (ran, "
                "never banked) · %d moved under their proof (not banked)"
                % (self.hits, n_total, self.carried, (" (%s)" % _by) if _by else "", self.stores, self.misses,
                   self.unkeyable, self.moved))

    def count_carried(self, by):
        """REG-3046 - one served hit another PC earned, by who carried it."""
        with self.lock:
            self.carried += 1
            _b = str(by or "another PC")
            self.carried_by[_b] = self.carried_by.get(_b, 0) + 1


def _prove_cache_off():
    """HEART2_PROVE_CACHE=0 - the ONE spelling of the cache's off switch, asked by the push (open_cache) and by #186's
    census (_census_cache). -> bool"""
    if str(os.environ.get("HEART2_PROVE_CACHE", "1")).strip().lower() in ("0", "no", "off", "false"):
        return True
    return False


def open_cache(say=print):
    """The cache prove(push=True) hands to _prove_push -> _VerdictCache | None (HEART2_PROVE_CACHE=0: closed, said).
    R2: a push's first open also folds every checkout's own pre-R2 red memory into the machine's."""
    _red_fold_checkouts(say)
    if _prove_cache_off():
        say("  #42 P3 CACHE: OFF for this run (HEART2_PROVE_CACHE=0) - every proof runs, nothing is banked")
        return None
    cache = _VerdictCache(say=say)
    seed = os.environ.get("HEART2_SHARD_SEED") or ""
    if seed and _SHARD.get("spec"):                  # REG-2961 - a CI proof shard only; never this machine's store
        n, why = cache.seed_from(seed)
        say("  REG-2961 SEED: %s" % ("%d proof(s) an earlier run banked may be served, each only under the key this "
                                    "checkout's bytes give it" % n if why is None else
                                    "%s is not read (%s) - nothing is seeded, every proof of this shard runs"
                                    % (os.path.basename(seed), why)))
    return cache


def _age_say(ms):
    try:
        s = max(0, int(time.time() - float(ms) / 1000.0))
    except (TypeError, ValueError):
        return "an UNKNOWN time"
    return "%dm" % (s // 60) if s < 3600 else "%.1fh" % (s / 3600.0) if s < 86400 else "%.1fd" % (s / 86400.0)


def _declares_widths(proofs):
    """#42 — does any proof of this gate declare the viewports its defect shows at?"""
    return any(isinstance(pr, dict) and "widths" in pr for pr in (proofs or []))


# REG-2602 (2026-10-23) - A COHERENT VERSION BUMP KEEPS THE KEYS OF THE LAWS THAT NEVER READ THE VERSION.
# bump_version.py rewrites stamp lines in bible.html, control_app.py, tv_diablo.py, WINDOWS_SHIP.json, RESUME_HERE.md,
# BLUEPRINT.md and the TASKS.md ship table, and 824 of 1024 laws hold one of those files, so every ship re-proved ~80%
# of the census. gate_ledger's own rule decides who may ignore it (STAMP_SURFACES, reads_version): a law whose name or
# script speaks of the version, whose closure holds a version-reader module, or whose proof's own text names a version
# keeps raw bytes. The rest hash those files with each WHOLE stamp line replaced by its kind - and only while the tree's
# stamps agree on one version, so a hand bump of one surface is a byte change like any other.
# only the count varies: the row's words are fixed, so no free text rides through
_STAMP_EXTRA = {"RESUME_HERE.md": (("gates", re.compile(r"^\| gates registered \| \d+ \*\(when this was written — ask run_gates for now\)\* \|$")),)}
_PROOF_VERSIONISH = re.compile(r"\bv\d+(?:\.\d+)*\b")


def _ledger():
    import gate_ledger as _GL  # the stamp rule's one home; heart2 imports it only when a key asks
    return _GL


def _inert(m):
    """Every free-text group of one stamp match (build name, notes, ship subjects) is inert words that leak nothing -
    stamp_leak's own two checks, as bump_version and gate_ledger ask them, LESS the one that reads this machine. -> bool

    ⚠ REG-3191 - THIS ANSWER IS KEY MATERIAL, SO IT MAY NOT DEPEND ON THE MACHINE THAT ASKS. leak_problem's last check
    refuses free text holding THIS machine's home path or user name (guest_profile._secrets) - right for a bump that
    publishes from here, wrong for a key: a stamp line is masked on one machine and kept raw on another, so the same
    bytes give two keys. MEASURED 2026-11-05 on his Mac at v3864 (9d9485ea6): GitHub's runner (home /home/runner) read
    every ship row naming its "runners" as a leak and kept it raw; his Mac masked it. The keys his Mac gave matched
    GitHub's for 78 of the 209 proofs of frame.release's guards - exactly the unmasked ones - so the import dropped the
    rest (REG-2596) and the river stayed shut until this PC re-proved them. Computed on his Mac with HOME=/home/runner,
    test_vault_l1_router_files_every_item's ten keys were GitHub's ten, byte for byte. Without the machine check: 209
    of 209 agree (a Windows home too), and every key his Mac gave before is unchanged. Soundness is untouched: what
    makes a masked line safe is free_text_problem (inert words only) and the law's literal counts (_literal_counts)."""
    import stamp_leak
    for g in ("f", "g", "s", "rest"):
        if g in m.re.groupindex and m.group(g) is not None:
            t = m.group(g).strip()
            while len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"":
                t = t[1:-1].strip()
            if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t, machine=False):
                return False
    return True


def _stamp_masked(rel, data):
    """`data` (bytes) with every whole stamp line of `rel` whose free text is inert replaced by its kind -> (bytes, the
    masked-away lines as one text) | None when it will not decode. A line with code riding on it, or a note that is
    not inert words, is not a stamp line and stays as it is."""
    GL = _ledger()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    out, away = [], []
    for line in text.split("\n"):
        bare = line[:-1] if line.endswith("\r") else line
        if rel == "TASKS.md":
            m = next((m for r in (GL._TASK_NEW, GL._TASK_SHIPPED) for m in [r.match(bare)]
                      if m), None)
            if m is not None and _inert(m):   # the strict row forms only: a loose row's free text is unchecked
                if not (out and out[-1] == "\0STAMP:ship"):   # a bump ADDS a row: the run of rows is one mark
                    out.append("\0STAMP:ship")
                away.append(bare)
                continue
        else:
            k = GL.stamp_kinds(rel, bare)
            if k is None:
                k = next(((kind, m) for kind, pat in _STAMP_EXTRA.get(rel, ()) for m in [pat.match(bare)] if m), None)
            if k is not None and _inert(k[1]):
                out.append("\0STAMP:" + k[0])
                away.append(bare)
                continue
        out.append(line)
    return "\n".join(out).encode("utf-8"), "\n".join(away)


def _literal_counts(lits, text):
    """gate_ledger.literal_hit's measure, taken at key time over one surface's masked-away stamp text: how often each
    literal of the law's own script occurs (gate_ledger's case-free count AND the exact one), how often each regex it
    hands re.* matches, and each such regex's words. A string-count or forbidden-string law holds the string it checks,
    so its verdict can move over a masked line only if one of these counts moves. -> [..]"""
    GL = _ledger()
    low = text.lower()
    every, rx = lits
    out = []
    for lit in sorted(every):
        out.append((lit, GL._count(low, lit.lower()), text.count(lit)))
    for pat in sorted(rx):
        try:
            hits = len(re.findall(pat, text)), len(re.findall(pat, text, re.I | re.M))
        except (re.error, RecursionError):
            hits = None
        out.append(("re", pat, hits))
        for w in sorted(set(GL._WORD.findall(re.sub(r"\\[A-Za-z]", " ", pat).lower()))):
            out.append(("re:" + w, GL._count(low, w)))
    return out


def _tree_version(repo):
    """The one version every required stamp surface of `repo` carries -> 'vN' | None (a surface missing, unreadable,
    with no stamp line, or two versions anywhere)."""
    GL = _ledger()
    seen = set()
    for rel in sorted(GL._STAMP_REQUIRED - {"TASKS.md"}):
        try:
            with open(os.path.join(repo, rel), encoding="utf-8") as fh:
                lines = fh.read().split("\n")
        except (OSError, UnicodeDecodeError):
            return None
        got = set()
        for line in lines:
            k = GL.stamp_kinds(rel, line[:-1] if line.endswith("\r") else line)
            if k is not None and "v" in k[1].re.groupindex:
                got.add(k[1].group("v"))
        if not got:
            return None
        seen |= got
    return next(iter(seen)) if len(seen) == 1 else None


def _law_reads_version(name, law_path, imported):
    """gate_ledger's reads_version + scans_content, over a law file and the module names its closure IMPORTS (a
    reader-only module a hub merely names in a string - run_gates describes windows_boot_check - is never run by the
    law). Unreadable counts as yes."""
    GL = _ledger()
    if GL._VERSION_NAME.search(str(name or "")) or str(name or "") in GL._ALWAYS_RERUN:
        return True
    if any(os.path.basename(r)[:-3] in imported for r in GL._VERSION_READER_ONLY):
        return True
    try:
        with open(law_path, encoding="utf-8", errors="replace") as fh:
            return bool(GL._VERSION_WORDS.search(fh.read()))
    except OSError:
        return True


def _proof_key(pr):
    """#42 — one red-proof as a comparable string: two entries are the same declaration exactly when these agree."""
    return json.dumps(pr, sort_keys=True, default=str)


def push_order(have, base_proofs=None, changed=None, anchor_off=None):
    """#42 P2 — the order a push-time run proves in, the likeliest to fail FIRST. -> ({gate: [idx]}, [gate], counts)

    have         [(name, filename, proofs)]
    base_proofs  {filename: [proof] | None} as the push base holds them - [] for a gate file the base does not have
                 (every entry NEW), None for one whose base RED_PROOF cannot be read (nothing counts as changed there);
                 the whole argument None = the base is unknown, so no entry ranks as changed (the caller says so)
    changed      set of repo-relative paths changed since the base, or None (unknown)
    anchor_off   callable(proof) -> True when its anchor does not match as declared in the tree being proved

    Score per proof: 4 anchor off · 2 entry new or changed · 1 its tampered file changed. Ties keep RED_PROOF order;
    gates go by their best-scored proof, ties in the order given. It ORDERS - it decides no verdict (_prove_one does).
    Pure, so the law drives it with fixtures."""
    order, rank, counts = {}, {}, {"anchor": 0, "entry": 0, "target": 0}
    for pos, (name, filename, proofs) in enumerate(have):
        base = None if base_proofs is None else base_proofs.get(filename)
        seen = None if base is None else set(_proof_key(x) for x in base)
        scores = []
        for i, pr in enumerate(proofs or []):
            sc = 0
            if anchor_off is not None and anchor_off(pr):
                sc += 4
                counts["anchor"] += 1
            if seen is not None and _proof_key(pr) not in seen:
                sc += 2
                counts["entry"] += 1
            tgt = _proof_target_rel(pr)
            if changed is not None and tgt and tgt in changed:
                sc += 1
                counts["target"] += 1
            scores.append((-sc, i))
        order[name] = [i for _s, i in sorted(scores)]
        rank[name] = (min([s for s, _i in scores] or [0]), pos)
    return order, sorted(order, key=lambda n: rank[n]), counts


def _proof_target_rel(pr):
    """#42 — a proof's tampered file as a repo-relative path (tv/ first, then the root: resolve_proof_target's rule)."""
    rel = str((pr or {}).get("file") or "") if isinstance(pr, dict) else ""
    if not rel:
        return None
    return os.path.relpath(resolve_proof_target(HERE, rel), REPO).replace(os.sep, "/")


def _git(*args):
    """#42 — one read-only git question about this repo. -> (ok, stdout)"""
    try:
        import git_quiet as _gq
        r = _gq.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=30, env=_git_free_env())
    except Exception as _e:
        # the question could not be asked: said as a failed answer (ok False), which the caller reports as UNKNOWN
        return False, "git %s: %s" % (args[0] if args else "", type(_e).__name__)
    return r.returncode == 0, (r.stdout or b"").decode("utf-8", "replace")


def gates_for_tests(paths):
    """#242 - the gate names a set of changed tv/test_*.py files map to, by the hook's own rule. -> [name] (sorted)

    hooks/pre-push derives the push's changed-law set with an inline script: every registered gate whose argv names one
    of the files by basename, its name passing a bare-argument check. A pre-flight that proves a different set is the
    mistake measured on v3602 - 17 laws pre-proved where the hook proved 136 - so this is the same rule, and a law runs
    the hook's script beside it over the same files and requires the same answer."""
    try:
        import run_gates as _rg
    except Exception:
        return []
    changed = set(os.path.basename(str(p)) for p in (paths or []))
    safe = re.compile(r"^[A-Za-z0-9_.-]+$")
    out = []
    for g in getattr(_rg, "GATES", []):
        for part in (getattr(g, "argv", None) or []):
            if os.path.basename(str(part)) in changed:
                if safe.match(str(getattr(g, "name", "") or "")):
                    out.append(g.name)
                break
    return sorted(set(out))


def laws_that_read(paths):
    """#261 - gate names whose own test file mentions a changed file's basename. -> [name] sorted

    gates_for_tests answers only a changed tv/test_*.py. A law that scans another file
    (bible.html, control_app.py) is not in that set, so CI is the first time it runs.
    A basename without a dot, or shorter than 8 characters, is not a file name this
    question can ask: it would match inside unrelated words.
    The match is a substring of the law's source, which is what a grep of that law sees.
    """
    try:
        import run_gates as _rg
    except Exception:
        return []
    names = []
    for p in (paths or []):
        base = os.path.basename(str(p))
        if "." not in base or len(base) < 8 or not re.match(r"^[A-Za-z0-9_.-]+$", base):
            continue
        names.append(base)
    if not names:
        return []
    safe = re.compile(r"^[A-Za-z0-9_.-]+$")
    text_of = {}
    out = []
    for g in getattr(_rg, "GATES", []):
        gname = str(getattr(g, "name", "") or "")
        if not safe.match(gname):
            continue
        src_path = None
        for part in (getattr(g, "argv", None) or []):
            part = str(part)
            if part.endswith(".py") and os.path.basename(part).startswith("test_"):
                src_path = part
                break
        if not src_path or not os.path.isfile(src_path):
            continue
        if src_path not in text_of:
            with open(src_path, encoding="utf-8", errors="replace") as fh:
                text_of[src_path] = fh.read()
        text = text_of[src_path]
        if any(base in text for base in names):
            out.append(gname)
    return sorted(set(out))  # REG-2148 readers


def changed_gates():
    """#242 - THE PUSH'S OWN CHANGED-LAW SET, for a pre-flight. -> (names, base | None, why | None)

    The hook's order of bases (@{push}, else origin/main), the hook's committed range, files still on disk only."""
    base = None
    for ref in ("@{push}", "origin/main"):
        ok, out = _git("rev-parse", "--verify", "--quiet", ref)
        if ok and out.strip():
            base = ref
            break
    if base is None:
        return [], None, "neither @{push} nor origin/main resolves, so the changed-law set is UNKNOWN"
    rng = "@{push}.." if base == "@{push}" else "origin/main..HEAD"
    ok, out = _git("diff", "--name-only", rng)
    if not ok:
        return [], base, "git diff --name-only %s could not be read - UNKNOWN" % rng
    changed = [l.strip() for l in out.splitlines() if l.strip()]
    return _gates_for_changed(changed), base, None


def _gates_for_changed(changed):
    """REG-2189 - THE PRE-FLIGHT NOW INCLUDES THE LAWS THAT SCAN A CHANGED NON-TEST FILE. -> [name] sorted

    gates_for_tests answers only a changed tv/test_*.py. laws_that_read answers the laws whose own
    source scans a changed file like bible.html or control_app.py. Both existed; nothing joined the
    second to this set, so a push that changed only bible.html got an EMPTY pre-flight and its
    scanning laws ran first on CI (REG-2148's own defect, left unjoined). This merges the two, which
    is the whole reason laws_that_read was written. Pure: given the changed list, no git, no disk read
    beyond gates_for_tests' own existence check. [[the-unjoined-end]]"""
    test_files = [f for f in changed if re.match(r"^tv/test_.*\.py$", str(f).strip())]
    live = [f for f in test_files if os.path.isfile(os.path.join(REPO, f))]
    non_test = [f for f in changed if f not in test_files]
    return sorted(set(gates_for_tests(live)) | set(laws_that_read(non_test)))


def _push_changed():
    """#42 / REG-2599 - what this push changes: (base ref | None, {repo-relative path} | None UNKNOWN), the hook's own
    order of bases (@{push}, else origin/main), diffed against the tree being proved (the sandbox copies it)."""
    base = None
    for ref in ("@{push}", "origin/main"):
        ok, out = _git("rev-parse", "--verify", "--quiet", ref)
        if ok and out.strip():
            base = ref
            break
    if base is None:
        return None, None
    # -z: raw paths, never core.quotePath's quoted form (second eye: a law path with a space or é read as unchanged)
    ok, out = _git("-c", "core.quotePath=false", "diff", "--name-only", "-z", base)
    return base, (set(p for p in out.split("\0") if p) if ok else None)


def _direct_laws(have, changed):
    """REG-2599 - the gates of `have` whose OWN law file the push changes. -> set | None (the change is UNKNOWN)"""
    if changed is None:
        return None
    return set(n for n, filename, _p in have
               if os.path.relpath(os.path.join(HERE, filename), REPO).replace(os.sep, "/") in changed)


def _owes_here(run, name):
    """REG-2599 (#242 narrowed, Elad 2026-10-23) - does a proof ANOTHER tree banked owe this gate one clean run here?

    Only when the push changes the gate's own law file, or when what the push changes is unknown. A gate in the push
    for any other reason is served over byte-identical inputs and kept on the other tree's word: one clean run per such
    gate is what kept every imported proof from saving a minute on his Mac."""
    direct = getattr(run, "direct", None)
    return direct is None or name in direct


def _wave_owed(gates, by, run):
    """REG-2631 - the gates the clean wave would actually run, in order. -> [name]

    _wave_gate returns at once for a gate whose every proof the cache serves on this tree's word, but only after the
    wave has built a sandbox per lane for it: MEASURED on the box, 19 gates / 226 proofs all served, the wave ran 0 clean
    runs in 41-52 s of copying and deleting trees. The same question is asked here over the checkout's own tv/ - the
    bytes every sandbox copies - so a gate it leaves out is one the wave would have skipped. The wave is fail-fast
    ORDER, never a verdict: a gate wrongly left out is still proved, served or run by the main pass, as before."""
    cache = getattr(run, "cache", None)
    if cache is None:
        return list(gates)
    out = []
    for n in gates:
        _n, f, proofs = by[n]
        served = bool(proofs)
        for i in (run.order.get(n) or list(range(len(proofs)))):
            try:
                key = cache.key_for(HERE, n, f, proofs[i])[0]
            except Exception:
                key = None
            hit = cache.peek(key) if key is not None else None          # asked, not served: marks nothing
            if hit is None or (hit.get("tree") != TREE_ID and _owes_here(run, n)):
                served = False
                break
        if not served:
            out.append(n)
    return out


def _push_facts(have, say):
    """#42 — what push_order needs, read from git and the tree being proved. -> (base | None, order, gates, counts)"""
    base, changed = _push_changed()
    base_proofs = None
    if base:
        base_proofs = {}
        for _n, filename, _p in have:
            rel = os.path.relpath(os.path.join(HERE, filename), REPO).replace(os.sep, "/")
            ok, src = _git("show", "%s:%s" % (base, rel))
            if not ok:
                base_proofs[filename] = []           # the base has no such file: every entry is NEW
                continue
            try:
                # the SAME reader the prover uses, never a second one; read in memory - nothing is written
                base_proofs[filename] = _red_proofs_of_tree(ast.parse(src))
            except SyntaxError:
                base_proofs[filename] = None         # the base's file will not parse: UNKNOWN, nothing ranks as changed
    texts = {}

    def _anchor_off(pr):
        # ⚠ AN ORDERING HINT, NOT A VERDICT: _prove_one alone decides INVALID. This only puts the proof it will decide
        # INVALID first, so a rotted anchor refuses the push in one clean run instead of after every other proof.
        rel, find = str(pr.get("file") or ""), str(pr.get("find") or "")
        if not rel or not find:
            return True
        tgt = resolve_proof_target(HERE, rel)
        if tgt not in texts:
            texts[tgt] = _read_text(tgt)
        if texts[tgt] is None:
            return True
        got, want = texts[tgt].count(find), pr.get("matches")
        try:
            return got < 1 or (want is not None and got != int(want))
        except (TypeError, ValueError):
            return True        # a count nobody can read: _prove_one will refuse it, so it goes first

    order, gates, counts = push_order(have, base_proofs, changed, _anchor_off)
    return base, order, gates, counts


def _browser_slot(name):
    """#42 — the lock a gate is proved under at push time (a browser gate's), or a context that holds nothing."""
    import contextlib
    return _PUSH.browser_slot(name) if _PUSH is not None else contextlib.nullcontext()


def _bankable(verdict):
    """#42 P3 / REG-1988 - ONE RULE FOR WHAT THE VERDICT CACHE MAY BANK: a PROVEN, and nothing else. -> bool

    Two places ask it - the proof that just ran (_prove_push_one) and the gate after its closing clean run
    (_prove_gate_push) - and they used to spell it twice, `v == PROVEN` and `per[_i] == PROVEN`. Twice is the trap the
    v3604 prove found: a law's sabotage of ONE spelling stayed green because the other still refused the BLIND, so the
    law that guards "a BLIND is never banked" read BLIND itself. One definition, asked twice, sabotaged once."""
    return verdict == PROVEN


def _keep_for(sandbox, filename, pr):
    """REG-2640 - the inputs a proof's key always digests by bytes, traced or not: its tampered target, every
    PROOF_NEEDS file and the prover. -> {repo-relative path}"""
    repo = os.path.dirname(os.path.abspath(sandbox))
    rel = lambda p: os.path.relpath(os.path.normpath(p), repo).replace(os.sep, "/")   # noqa: E731
    keep = {rel(os.path.join(sandbox, "heart2.py")), rel(os.path.join(sandbox, "law_widths.py")),
            rel(os.path.join(sandbox, "gate_trace", "node_trace.cjs"))}   # REG-3319 - the node half of the trace
    tf = str(pr.get("file") or "") if isinstance(pr, dict) else ""
    if tf:
        keep.add(rel(resolve_proof_target(sandbox, tf)))
    for need in (proof_needs_in(os.path.join(sandbox, filename)) or ()):
        keep.add(rel(os.path.join(sandbox, need)))
    # every module of the static import closure stays a byte input: only a module the closure merely NAMES in a
    # string (run_gates lists every law) may be keyed by name, and only when no traced run opened it or its cache
    closure = set()
    law_inputs(sandbox, filename, [pr], parsed=_KEEP_PARSED, closure=closure)
    keep |= {rel(p) for p in closure}
    return keep


_KEEP_PARSED = {}     # REG-2640 - law_inputs' (path, size, mtime_ns) memo for _keep_for


def _final_key(cache, sandbox, name, filename, pr, key, entry):
    """REG-2640 - the key a PROVEN is banked under, taken when it is banked: the v2 key over the named data files no
    traced run of this law opened, or `key` (v1) when there are none or the v2 key cannot be taken. Updates `entry`.
    -> a callable returning the key (never raises: a narrower key is an optimisation, v1 is always sound)"""
    def take():
        if (isinstance(key, str) and key.startswith("pending-listing:")) or cache.lists(sandbox, filename):
            return _listing_key(cache, sandbox, name, filename, pr, entry)     # REG-2944 - v3 or nothing, never v1
        try:
            un = _trace_unread(filename, entry.get("inputs") or [], _keep_for(sandbox, filename, pr))
            if un:
                k2 = cache.key_for(sandbox, name, filename, pr, unread=un)[0]
                if k2 is not None:
                    entry.update(ident=cache.ident(name, filename, pr), unread=un)
                    return k2
        except Exception:
            pass
        entry.pop("ident", None)
        entry.pop("unread", None)
        return key
    return take


def _listing_key(cache, sandbox, name, filename, pr, entry):
    """REG-2944 - a listing law's v3 key, from what its traced runs listed, or None (never banked: said, and counted for
    the push record). A pending key is NEVER stored: a listing law with no complete in-tree trace runs every push."""
    repo = os.path.dirname(os.path.abspath(sandbox))
    why = None
    try:
        ls, why = _trace_listed(filename, repo, lambda rel: cache.ignored_in(repo, rel))
        if ls is not None:
            un = _trace_unread(filename, entry.get("inputs") or [], _keep_for(sandbox, filename, pr))
            k3, _r, why = cache.key_for(sandbox, name, filename, pr, unread=un, listed=ls)
            if k3 is not None and not str(k3).startswith("pending-listing:"):
                # REG-2981 - the #242 floor as a NUMBER: how many gitignored names its listed dirs held when it banked
                seen = sum(len(cache.ignored_in(repo, rel) or ()) for rel in ls)
                entry.update(ident=cache.ident(name, filename, pr), listed=list(ls), unread=list(un), ignoredSeen=seen)
                with cache.lock:
                    cache.traced["banked"] += 1
                return k3
    except Exception as _le:
        why = "its listing key could not be taken (%s)" % type(_le).__name__
    with cache.lock:
        cache.traced["refused"] += 1
        w = str(why or "no key")[:80]
        cache.traced["why"][w] = cache.traced["why"].get(w, 0) + 1
    return None


def _prove_push_one(sandbox, name, filename, pr, idx, say, why):
    """#42 — ONE proof at push time: reused from the verdict cache when every keyed byte is identical (P3), otherwise
    run at the widths it declares and banked only when it came back PROVEN. -> verdict (the PUSH TIME block above)

    #186 - the serve and the bank are _cache_serve and _cache_bank, the ONE implementation the self-prove census asks
    too (_census_one): two copies of "may this verdict be reused / banked" would be two rules. [[copy-drift]]"""
    cache = _PUSH.cache if _PUSH is not None else None
    served, key, rels = _cache_serve(cache, sandbox, name, filename, pr, idx, say)
    if served is not None:
        return served
    v = _prove_push_one_run(sandbox, name, filename, pr, idx, say, why)
    _cache_bank(cache, sandbox, name, filename, pr, idx, say, key, rels, v)
    return v


def _cache_serve(cache, sandbox, name, filename, pr, idx, say, own_only=None):
    """#42 P3 (and #186's census) - proof `idx` served from the verdict cache when every keyed byte is identical.
    -> (PROVEN | None, key | None, [repo-relative inputs]); None = not served: run it, then hand the key to _cache_bank
    REG-3191 - `own_only` (None: is this gate in the census's _CENSUS["here"] - an environment self-check gate, or a
    safety-net run; always empty on a push): a PROVEN another tree banked is not served - it is judged on this PC; one
    this tree banked still is."""
    if own_only is None:
        own_only = name in (_CENSUS.get("here") or ())
    key, rels = None, []
    # REG-3118 (#186, the second eye on v3840) - A PROOF THIS PC CANNOT RUN IS NEVER SERVED, AT PUSH TIME EITHER. Only the
    # census held this (it dropped its cache for the proof); _prove_push_one served any hit first, so a node law the ALT
    # proved and carried could read PROVEN on Dean's push - a PC with no node that never judged it. Held here, in the ONE
    # serve both callers ask: a declared need this PC lacks, or cannot probe, is judged here, never served, banks nothing.
    if cache is not None and isinstance(pr, dict) and pr.get("needs"):
        try:
            _lacks = host_lacks(pr.get("needs"))[0]
        except Exception:
            _lacks = None
        if _lacks is not False:
            return None, None, []
    if cache is not None:
        label = "%s[%d]" % (name, idx)
        # ⚠ THE CACHE MAY COST A RE-PROVE, NEVER A VERDICT. key_for raising here (a RecursionError from ast.parse on a
        # pathological module, a relpath across volumes, anything unforeseen) would have been recorded BLIND by
        # _prove_gate_push and refused the push over the cache's own bookkeeping. Caught: UNKEYABLE, said, and the
        # proof runs exactly as it would with no cache at all.
        try:
            key, rels, kwhy = cache.key_for(sandbox, name, filename, pr)
        except Exception as _ke:
            key, rels, kwhy = None, [], "taking its key raised %s (%s)" % (type(_ke).__name__, str(_ke)[:80])
        _mark(key=key, u=kwhy if key is None else None)         # REG-2353 - the push record's keyable / unkeyable
        if key is None:
            cache.count("unkeyable")
            cache.say_once(name, kwhy, "     %-52s   ↳ #42 P3: not cacheable - %s; every proof of this law runs on "
                                       "every push" % (label, kwhy))
        else:
            _own = cache.peek(key) if own_only else None
            if own_only and _own is not None and _own.get("tree") != TREE_ID:
                cache.count("misses")         # REG-3191 - another tree's word is not this PC's self-check
                cache.say_once(name, "REG-3191 own-only", "     %-52s   ↳ REG-3191: judged on this PC - another tree's "
                                                         "PROVEN is not served to it here" % label)
                return None, key, rels
            hit = cache.lookup(key)
            if hit is not None:
                cache.count("hits")
                if isinstance(hit.get("carried"), dict):
                    cache.count_carried(hit["carried"].get("by"))     # REG-3046 - served, and another PC earned it
                _srv = getattr(_CLEAN, "served", None)
                if isinstance(_srv, list):
                    _srv.append((idx, hit.get("tree"), key, hit))  # REG-2587 - which tree proved what this gate reuses
                _mark(f="hit", a="hit")                          # REG-2353 - forecast and taken: served, not run
                # the census keeps the age this proof was MEASURED at, never this run's clock [[stale-reading]]
                cache.reused_at(name, idx, hit["provedAt"])
                if hit.get("ckpt") and getattr(_PUSH, "ckpt", None) is not None:
                    with _PUSH._lock:                    # #150 - banked at a checkpoint of a gate that never closed
                        _PUSH.ckpt["resumed"] += 1
                        _PUSH.ckpt["resumedS"] += float(hit.get("ckptS") or 0)
                say("     %-52s %s (cached %s: %d byte-identical input(s), proved %s ago%s - not re-run)"
                    % (label, PROVEN, key[:8], len(hit.get("inputs") or rels), _age_say(hit.get("provedAt")),
                       (" at %s" % hit["at"]) if hit.get("at") else ""))
                return PROVEN, key, rels
            cache.count("misses")
    return None, key, rels


def _cache_bank(cache, sandbox, name, filename, pr, idx, say, key, rels, v, by=None):
    """#42 P3 (and #186's census) - bank proof `idx`'s PROVEN under its key, TAKEN AGAIN after the run: a key that moved
    banks nothing. Inside a gate (_CLEAN.pending a list) the entry waits for the gate's closing clean run. `by` names who
    proved it ("census": it ran the whole law, so it names no declared widths). -> None"""
    if key is not None and _bankable(v):
        # ⚠ KEYED AGAIN AFTER THE RUN: the tamper wrote and restored the target, and a law may write beside itself; a key
        # that moved means the bytes proved are not the bytes on disk, and a PROVEN banked under them would be a lie.
        # And the same rule as above: a key that cannot be taken again is a tree that moved - PROVEN stands.
        _how = "its key changed while it ran"
        try:
            again, rels2, _w2 = cache.key_for(sandbox, name, filename, pr)
        except Exception as _ke:
            again, _how = None, "its key could not be taken again: %s" % type(_ke).__name__
        if again == key:
            try:
                import law_widths as _LW
                try:
                    _at = _LW.declared(pr)
                except ValueError:
                    _at = None
                _entry = {"verdict": PROVEN, "gate": name, "proof": idx, "why": str(pr.get("why") or "")[:120],
                          "at": _LW.label(_at) if _at else "", "provedAt": int(time.time() * 1000),
                          "target": str(pr.get("file") or ""), "inputs": rels, "tree": TREE_ID}
                if by:
                    _entry.update(by=by, at="")          # #186 - a census ran the whole law: no declared widths
                _pend = getattr(_CLEAN, "pending", None)
                if isinstance(_pend, list):
                    # REG-1988 - banked by _prove_gate_push after the closing run; REG-2640 - and keyed THEN, so the
                    # closing run's own trace is in the union the unread set is taken from
                    _pend.append((idx, _final_key(cache, sandbox, name, filename, pr, key, _entry), _entry))
                else:
                    key = _final_key(cache, sandbox, name, filename, pr, key, _entry)()
                    if key is None:                      # REG-2944 - a listing law whose trace cannot key it
                        cache.count("moved")
                    else:
                        cache.store(key, _entry)
                        cache.count("stores")
            except Exception as _se:
                cache.count("moved")
                say("     %-52s   ↳ #42 P3: could not be banked (%s) - PROVEN stands, nothing is banked"
                    % ("%s[%d]" % (name, idx), type(_se).__name__))
        else:
            cache.count("moved")
            say("     %-52s   ↳ #42 P3: the tree moved under this proof (%s) - PROVEN stands, "
                "nothing is banked" % ("%s[%d]" % (name, idx), _how))


def _prove_push_one_run(sandbox, name, filename, pr, idx, say, why):
    """#42 — the run itself: ONE proof at the widths it declares (the PUSH TIME block above). -> verdict"""
    label = "%s[%d]" % (name, idx)
    widths = None
    if isinstance(pr, dict) and "widths" in pr:
        import law_widths as _LW
        try:
            widths = _LW.declared(pr)
        except ValueError as _we:
            say("     %-52s %s — its 'widths' cannot be read (%s): a declaration nobody can read is refused, never "
                "guessed at" % (label, INVALID, _we))
            return INVALID
    if not widths:
        return _prove_one(sandbox, name, filename, pr, idx, say, why=why)
    v = _prove_one(sandbox, name, filename, pr, idx, say, widths=widths, why={})
    if v != UNPROVABLE:
        return v
    # ⚠ AN UNPROVABLE AT A SAMPLE IS NOT KEPT: it is not failed, so keeping it would let a restriction that broke the
    # clean run wave through a proof the full run might find BLIND. The full run's verdict is the one that stands.
    say("     %-52s   ↳ #42: its declared widths could not judge it - re-proved at EVERY width; that verdict stands"
        % label)
    return _prove_one(sandbox, name, filename, pr, idx, say, why=why)


def _push_gate_verdict(per):
    """#42 — a push-time gate's verdict from its proofs' (None = NOT RUN). A failure counts wherever it was found; a
    gate the stop cut short is NOT_RUN - never PROVEN on the proofs that happened to run first."""
    got = [v for v in per if v is not None]
    if BLIND in got:
        return BLIND
    if INVALID in got:
        return INVALID
    if len(got) < len(per):
        return NOT_RUN
    # #145 (the v3546 eye) - every proof judged only elsewhere is UNPROVABLE here, on the push path as on _prove_gate's:
    # this list fell through to PROVEN, and a push banked a gate no proof had judged on this PC
    if got and all(v == ELSEWHERE for v in got):
        return UNPROVABLE
    return UNPROVABLE if UNPROVABLE in got else PROVEN


def _wave_gate(sandbox, name, filename, proofs, say, run):
    """REG-1992 — THE CLEAN WAVE: one untampered run of this gate, before ANY gate's tampered runs. -> (NOT_RUN, [None])

    MEASURED: the v3601 push was refused at minute 39 and the v3602 push at minute 80, both on a law ALREADY RED
    untampered - the cheapest verdict the prover makes (one run per gate), scheduled gate by gate among the expensive
    ones. Now every gate's clean run goes first across the lanes, so a law that is red here refuses the push in the
    wave's minutes; the main pass reuses the wave's green verdict for its first proof (_prove_one seeds it) and its
    closing run asks it again in that pass's own sandbox. The clean run asked is exactly the one the gate's first proof
    in run order would ask (its widths). A gate whose every proof the verdict cache would serve is not asked: its PROVENs
    were judged over byte-identical inputs on this machine. Nothing here is a verdict: the wave answers green, red, or
    nothing, and only a red is said."""
    _CLEAN.runs = {}
    _CLEAN.pending = None
    _held = []
    _q = lambda *a, **k: _held.append(a[0] if a else "")      # noqa: E731 - lines are said only for a red
    try:
        order = run.order.get(name) or list(range(len(proofs)))
        if getattr(run, "deadline", None) is not None and time.time() >= run.deadline:
            return NOT_RUN, [None] * len(proofs)        # REG-3212 - past the run's deadline the main pass cuts it, named
        cache = run.cache
        if cache is not None:
            _all = True
            for i in order:
                try:
                    key, _r, _w = cache.key_for(sandbox, name, filename, proofs[i])
                except Exception:
                    key = None
                _hit = cache.peek(key) if key is not None else None   # REG-2353 - asked, not served: marks nothing
                # #242 - a proof banked in ANOTHER tree is reused, but its gate still owes this tree one clean run: a
                # law that reads live state only main holds can be red here and green there
                if _hit is None or (_hit.get("tree") != TREE_ID and _owes_here(run, name)):   # REG-2599
                    _all = False
                    break
            if _all:
                return NOT_RUN, [None] * len(proofs)
        for i in order:
            if run.stop.is_set():
                break
            pr = proofs[i]
            widths = None
            if isinstance(pr, dict) and "widths" in pr:
                import law_widths as _LW
                try:
                    widths = _LW.declared(pr)
                except ValueError:
                    continue                    # the main pass refuses an unreadable declaration (INVALID); not the wave's
            why = {}
            try:
                v = _prove_one(sandbox, name, filename, pr, i, _q, widths=widths, why=why, clean_only=True)
            except Exception as _we:
                v = None
                _held.append("    the wave's clean run raised %s - left to the main pass" % type(_we).__name__)
            if v == ELSEWHERE or v == INVALID:
                continue                        # this proof is not judged here; the next one may be
            if v == UNPROVABLE and why.get("red"):
                for ln in _held:
                    say(ln)
                _why = "the law is ALREADY RED untampered, so no proof of it can be judged"
                if run.fail(name, i, UNPROVABLE, _why):
                    say(run.owe_line(name, i, UNPROVABLE, _why) if run.keep_going else
                        "  ⛔ #42 FAIL FAST (REG-1992 clean wave) — %s[%d] is ALREADY RED untampered. Found before any "
                        "tampered run: every proof is NOT RUN and the push is refused on this one." % (name, i))
            break
        with run._qlock:
            for _ck, _e in (_CLEAN.runs or {}).items():
                run.clean_wave[_ck] = (_e.get("ok"), _e.get("tail"))
    finally:
        _CLEAN.pending = None
        _CLEAN.runs = None
    return NOT_RUN, [None] * len(proofs)


def _clean_here(sandbox, name, filename, proofs, per, say, run):
    """REG-2587 (#242 on a small push) - a gate whose proofs the cache served from ANOTHER tree is run clean HERE once.

    The clean wave (REG-1992) gives such a gate its clean run in this tree - but the wave runs only when a push has more
    gates than lanes, and a gate whose every proof is served runs no law in the main pass. So a push of 1 gate (or of
    as many gates as lanes) reused another tree's PROVENs for a law that may be red HERE (live state only this tree
    holds) and never asked. Now: when a served proof names another tree (or none) and nothing ran this gate's law
    untampered here in this run, its clean run is asked here. GREEN keeps the verdicts; RED fails fast as the wave does
    and every PROVEN becomes UNPROVABLE; a clean run that cannot finish turns them UNPROVABLE too (never kept on a
    guess). A gate no proof of which can be asked here (ELSEWHERE everywhere) keeps them and SAYS so.
    -> per (verdicts in RED_PROOF order)"""
    _CLEAN.green_here = False                            # REG-2589 - did this law run GREEN untampered in this tree?
    foreign = sorted(s[0] for s in (getattr(_CLEAN, "served", None) or []) if s[1] != TREE_ID)
    if not foreign or run.stop.is_set():
        return per
    if not _owes_here(run, name):
        say("     %-52s   ↳ REG-2599: %d proof(s) were proved in another tree over byte-identical inputs - kept without a "
            "clean run here: this push does not change its law" % (name, len(foreign)))
        return per
    if getattr(_CLEAN, "runs", None):
        # a proof of this gate ran its clean run here in this pass; the closing run (_closing_clean) still judges it
        _CLEAN.green_here = any(r.get("ok") is True for r in _CLEAN.runs.values())
        return per
    # second eye (REG-2589): the wave's row must be THIS gate's clean run - its file AND its argv, script and timeout
    # (two gates may share a file) - and every such row green; a wave row of another gate on the same file proves nothing
    _ex, _to, _sc = gate_spec(name)
    _mine = [wv for ck, wv in (getattr(run, "clean_wave", None) or {}).items()
             if ck[0] == filename and ck[1] == repr(_ex) and ck[2] == repr(_sc) and ck[4] == _to]
    if _mine and all(wv[0] is True for wv in _mine):
        _CLEAN.green_here = True
        return per                                       # the wave ran it clean here (a red stopped the run there)
    v, why, asked, skips = None, {}, None, set()
    for i in (run.order.get(name) or list(range(len(proofs)))):
        if run.stop.is_set():
            return per                                   # another gate stopped the run: it is refused already
        pr = proofs[i]
        widths = None
        if isinstance(pr, dict) and "widths" in pr:
            import law_widths as _LW
            try:
                widths = _LW.declared(pr)
            except ValueError:
                skips.add(INVALID)                       # an unreadable declaration judges nothing here
                continue
        why = {}
        try:
            v = _prove_one(sandbox, name, filename, pr, i, say, widths=widths, why=why, clean_only=True)
        except Exception as _ce:
            v = None
            say("     %-52s   ↳ REG-2587: its clean run here raised %s (%s)" % (name, type(_ce).__name__,
                                                                            str(_ce)[:120]))
        if v == ELSEWHERE or v == INVALID:
            skips.add(v)
            continue
        asked = i
        break
    else:
        if skips == {ELSEWHERE}:
            say("     %-52s   ↳ REG-2587: %d proof(s) were proved in another tree and no proof of it can run on this "
                "PC (ELSEWHERE), so its clean run here is not asked - kept as served" % (name, len(foreign)))
            return per
        say("     %-52s   ↳ REG-2587 (#242): %d proof(s) were proved in another tree and no clean run of it could be "
            "asked here - none of them is kept" % (name, len(foreign)))
        return [UNPROVABLE if x == PROVEN else x for x in per]
    if v == CLEAN:
        say("     %-52s   ↳ REG-2587 (#242): %d proof(s) were proved in another tree; its clean run HERE is green"
            % (name, len(foreign)))
        _CLEAN.green_here = True
        return per
    red = v == UNPROVABLE and bool(why.get("red"))
    out = [UNPROVABLE if x == PROVEN else x for x in per]
    say("     %-52s   ↳ REG-2587 (#242): %d proof(s) were proved in another tree and its clean run HERE %s - "
        "none of them is kept" % (name, len(foreign), "is RED" if red else "could not finish"))
    _why = "the law is ALREADY RED untampered here, where another tree proved it"
    if red and run.fail(name, asked, UNPROVABLE, _why):
        say(run.owe_line(name, asked, UNPROVABLE, _why) if run.keep_going else
            "  ⛔ #42 FAIL FAST (REG-2587) — %s is ALREADY RED untampered in this tree; another tree's PROVENs are not "
            "kept and the push is refused on this one." % name)
    return out


def _rebank_here(cache, name, per, say):
    """REG-2589 - after this law ran GREEN untampered in THIS tree, the PROVENs another tree banked for it are banked
    again under this tree, so the next push over the same bytes owes #242 nothing more (REG-2587 asked its clean run on
    EVERY push until a tampered run here re-proved them). Only a proof still PROVEN after the closing clean run; the
    entry keeps the provedAt it was MEASURED at (the census age) and says where it was proved. -> how many"""
    if cache is None or not getattr(_CLEAN, "green_here", False):
        return 0
    n, now = 0, int(time.time() * 1000)
    for _s in (getattr(_CLEAN, "served", None) or []):
        if len(_s) < 4 or _s[1] == TREE_ID or not isinstance(_s[3], dict) or per[_s[0]] != PROVEN:
            continue
        cache.store(_s[2], dict(_s[3], tree=TREE_ID, provedIn=_s[1], cleanHereAt=now))
        n += 1
    if n:
        say("     %-52s   ↳ REG-2589: %d proof(s) another tree proved are banked under THIS tree - its clean run here "
            "was green, so the next push over these bytes does not ask it again" % (name, n))
    return n


def _timeout_owed(run, name, cut, why, say):
    """REG-3212 - every proof of `name` its bound cut is OWED as TIMEOUT (UNKNOWN, never PROVEN), each by name, and said."""
    reason = "cut at its bound - %s; UNKNOWN, never PROVEN" % why
    with run._lock:
        run.cut.extend((name, i) for i in cut)
    for i in cut:
        run.fail(name, i, TIMEOUT, reason)
    say("  ⏱ REG-3212 TIMEOUT — %s: %d proof(s) cut at their bound (%s): %s. They are OWED and named, never PROVEN."
        % (name, len(cut), why, ", ".join("[%d]" % i for i in cut[:12]) + (" …" if len(cut) > 12 else "")))


def _prove_gate_push(sandbox, name, filename, proofs, say, run):
    """#42 — one gate's proofs at push time: in the run's order, each at its declared widths, the whole run stopped at
    the first failure. -> (verdict | NOT_RUN, [verdict | None per proof, in RED_PROOF order])

    The per-proof rule is _prove_gate's - a proof that raises is BLIND and is recorded - only the order, the widths and
    the stop are new."""
    if getattr(run, "wave", False):
        return _wave_gate(sandbox, name, filename, proofs, say, run)     # REG-1992 - the clean wave's pass
    if getattr(run, "keep_going", False) and run.failed(name):
        # REG-2591 - its clean wave run was RED: it is owed already, and running its law again proves nothing new
        say("     %-52s NOT RUN — REG-2591: owed a fix already (its clean run was red); the shard keeps going" % name)
        return NOT_RUN, [None] * len(proofs)
    got = {}
    # ⚠⚠ REG-1988 — THE PUSH PATH NEVER GOT REG-1669. _prove_gate hands a push-time gate here BEFORE it sets _CLEAN.runs,
    # so at push time every proof still ran the untampered law first: a gate with N proofs paid 2N law runs where N+2 do
    # - the run the hook pays on every push, the one he waits on. MEASURED on the v3602 pushes: 893 proofs over 131
    # gates, ~1786 runs where ~1155 do, and 168 of the 241 gate minutes of 15 pushes were this stage. Now the gate's
    # proofs share one clean run here too, and the CLOSING clean run (_closing_clean, the one rule) must still be green.
    # A proof proved here is banked only AFTER that closing run: a PROVEN it turns UNPROVABLE is never stored.
    _CLEAN.runs = {}
    _CLEAN.pending = []                                  # (index, key, entry) a PROVEN waits in until the closing run
    _CLEAN.served = []                                   # REG-2587 - (index, tree) of each proof the cache served
    _CLEAN.ckpt_keys = []                                # #150 - (key, entry) this gate's checkpoints banked
    try:
        _order = run.order.get(name) or list(range(len(proofs)))
        _ckpt = {"on": True}                             # #150 - False once a checkpoint was not green (the closing run decides)
        _g0, _cut, _cut_why = time.time(), [], None      # REG-3212 - this gate's clock, and what its bound cut
        _BOUND.t0 = _g0                                  # REG-3212 - a run of this gate's proofs is killed at its cap
        _BOUND.cap = _gate_cap_for(name, getattr(run, "gate_cap", None))   # REG-3317 - its own declared cap, if larger
        for _n, i in enumerate(_order):
            if run.stop.is_set():
                break
            _bound = _past_bound(run, _g0, cap=_BOUND.cap)
            if _bound is not None and not _served_here(run.cache, sandbox, name, filename, proofs[i]):
                _cut.append(i)                           # REG-3212 - TIMEOUT: not run, never PROVEN, owed and named
                _cut_why = _cut_why or _bound
                continue
            if _ckpt["on"] and run.cache is not None and len(getattr(_CLEAN, "pending", None) or []) >= CHECKPOINT_EVERY:
                _ckpt["on"] = _checkpoint_bank(name, got, say, run)      # #150 (REG-2942) - before proof i, never after the last
            why = {}
            _MARK.m = {"t0": time.time()}                # REG-2353 - what this proof was forecast to do, and did
            _BOUND.cut = None
            try:
                got[i] = _prove_push_one(sandbox, name, filename, proofs[i], i, say, why)
            except Exception as _pe:
                say("    proof %d raised %s — recorded BLIND: %s" % (i, type(_pe).__name__, str(_pe)[:120]))
                got[i] = BLIND
            finally:
                _m, _MARK.m = (getattr(_MARK, "m", None) or {}), None
            if getattr(_BOUND, "cut", None) is not None and got.get(i) != PROVEN:
                # REG-3212 - a run of this proof was KILLED at its bound: TIMEOUT (owed, named), never the law's verdict
                _cut.append(i)
                _cut_why = _cut_why or _BOUND.cut
                got.pop(i, None)
                with run._lock:
                    run.proofs[(name, i)] = dict(_m, v=TIMEOUT, s=round(time.time() - _m.get("t0", time.time()), 1))
                continue
            with run._lock:
                run.proofs[(name, i)] = dict(_m, v=got.get(i), s=round(time.time() - _m.get("t0", time.time()), 1))
            reason = {BLIND: "the tamper ran and the law stayed GREEN",
                      INVALID: "the red-proof cannot tamper as declared"}.get(got[i])
            if got[i] == UNPROVABLE and why.get("red"):
                reason = "the law is ALREADY RED untampered, so no proof of it can be judged"
            if reason:
                if run.fail(name, i, got[i], reason):
                    say(run.owe_line(name, i, got[i], reason) if run.keep_going else
                        "  ⛔ #42 FAIL FAST — %s[%d] %s: %s. The run stops here: every proof not yet run is NOT RUN, "
                        "and the push is refused on this one." % (name, i, got[i], reason))
                break
        _BOUND.t0, _BOUND.cut, _BOUND.cap = None, None, None   # REG-3212 - the closing runs answer to the hard stop only
        per = [got.get(i) for i in range(len(proofs))]
        _pre = list(per)
        per = _clean_here(sandbox, name, filename, proofs, per, say, run)   # REG-2587 - #242 on a push with no wave
        _before = list(per)
        per = _closing_clean(name, per, say)             # REG-1988 - None (NOT RUN) passes through untouched
        if getattr(_BOUND, "cut", None) is not None:
            # REG-3212 - the clean run that had to CONFIRM this gate's PROVENs was killed at the hard stop: they are not
            # PROVEN (never banked) and not the law's defect either - TIMEOUT, owed by name, like a proof never started
            _srv = set(x[0] for x in (getattr(_CLEAN, "served", None) or []))     # served: judged by its own rules
            _lost = [j for j in range(len(per)) if _pre[j] == PROVEN and per[j] != PROVEN and j not in _srv]
            _cut.extend(_lost)
            _cut_why = _cut_why or _BOUND.cut
            for j in _lost:
                per[j] = None
        if _cut:
            _timeout_owed(run, name, sorted(set(_cut)), _cut_why, say)
        _f = run.first if (run.first and run.first[0] == name) else None
        if _f is not None and _before[_f[1]] in (BLIND, INVALID) and per[_f[1]] == UNPROVABLE:
            # FAIL CLOSED: the stop already stands. Only its REASON is corrected - the failure may be the drift.
            say("     %-52s   ↳ REG-1988: the closing clean run went RED, so the sandbox drifted across this gate's "
                "proofs and the %s above may be that drift, not the law; the push stays refused. Reproduce: "
                "python3 tv/heart2.py --prove %s" % ("%s[%d]" % (name, _f[1]), _before[_f[1]], name))
        if run.cache is not None and getattr(_CLEAN, "ckpt_keys", None):
            if any(_before[_j] == PROVEN and per[_j] != PROVEN for _j in range(len(per))):
                _checkpoint_revoke(name, say, run)       # #150 - the closing run went RED after a green checkpoint
            else:
                _checkpoint_close(name, run)
        if run.cache is not None:
            for _i, _key, _entry in (getattr(_CLEAN, "pending", None) or []):
                if _bankable(per[_i]):
                    if callable(_key):                   # REG-2640 - the v2 key is taken after the closing run
                        _key = _key()
                    if _key is None:                     # REG-2944 - a listing law whose trace cannot key it
                        run.cache.count("moved")
                        continue
                    run.cache.store(_key, _entry)
                    run.cache.count("stores")
                    with run._lock:
                        run.proofs.setdefault((name, _i), {})["b"] = True     # REG-2353 - banked for its bytes
                else:
                    run.cache.count("moved")
                    say("     %-52s   ↳ #42 P3: not banked - the gate's closing clean run took its PROVEN away"
                        % ("%s[%d]" % (name, _i)))
            _rebank_here(run.cache, name, per, say)      # REG-2589 - after the closing run, never before it
    finally:
        _CLEAN.pending = None
        _CLEAN.runs = None
        _CLEAN.served = None
        _CLEAN.ckpt_keys = None
        _CLEAN.green_here = False
        _BOUND.t0, _BOUND.cut, _BOUND.cap = None, None, None
    if run.cache is not None:
        run.cache.flush()          # P3: what this gate proved reaches the disk now, not only at the end of the run
    return _push_gate_verdict(per), per


#: REG-2353 — the record the last prove(push=True) assembled; main() adds its exit and summary, then writes it
_PUSH_RECORD = {"record": None}


def _heart2_seams(env=None):
    """REG-2352 (#42 R11) — every inherited HEART2_* variable: each one changes what a push proves or banks. -> {k: v}"""
    env = os.environ if env is None else env
    return dict((k, str(env[k])) for k in sorted(env) if str(k).startswith("HEART2_"))


def _proof_ident(name, pr):
    """REG-2353 — a proof's identity as a banked entry records it (gate, target, why). -> tuple"""
    pr = pr if isinstance(pr, dict) else {}
    return (str(name), str(pr.get("file") or ""), str(pr.get("why") or "")[:120])


def _push_record(run, have, cache, n_proofs, results):
    """REG-2353 (#42 R16) — what this --push run forecast and did, proof by proof. -> dict (JSON; no absolute path)

    forecast `f`: the path a proof was going to take, decided before any run of it - hit (served by the cache), narrow
    (the red memory names the cases that caught it), full; None when it was decided without a run (ELSEWHERE, INVALID,
    no subject). actual `a`: hit / narrow / full / none, or notRun (the run stopped before it). `fell`: a narrowed pair
    that did not decide it. A proof that ran carries `missWhy`; one whose key the cache would serve when the run BEGAN
    and that still ran is a PROVE-ONCE VIOLATION (a banked proof re-run for the same bytes - a wrongful eviction)."""
    t0_ms = int(run.t0 * 1000)
    fc = {"hit": 0, "narrow": 0, "full": 0, "none": 0}
    ac = {"hit": 0, "narrow": 0, "full": 0, "none": 0, "notRun": 0}
    before = {}
    for e in (list(cache.entries.values()) if cache is not None else []):
        if isinstance(e, dict) and e.get("verdict") == PROVEN and isinstance(e.get("provedAt"), (int, float)) \
                and e["provedAt"] < t0_ms:
            ident = (str(e.get("gate")), str(e.get("target") or ""), str(e.get("why") or "")[:120])
            before[ident] = max(before.get(ident, 0), e["provedAt"])
    per, violations, unkeyable, fell, posix_only = [], [], 0, 0, []
    for name, _f, proofs in have:
        for i, pr in enumerate(proofs or []):
            m = run.proofs.get((name, i)) or {}
            if "v" not in m:
                ac["notRun"] += 1
                per.append({"g": name, "i": i, "a": "notRun"})
                continue
            f, a = m.get("f"), m.get("a") or "none"
            fc[f or "none"] = fc.get(f or "none", 0) + 1
            ac[a] = ac.get(a, 0) + 1
            row = {"g": name, "i": i, "f": f, "a": a, "v": m.get("v"), "s": m.get("s"), "b": bool(m.get("b"))}
            if m.get("u"):
                row["u"] = str(m["u"])[:160]
                unkeyable += 1
            if m.get("fellThrough"):
                row["fell"] = True
                fell += 1
            if m.get("posixOnly"):                       # REG-2357 (round 4) - caught only by cases that skip off POSIX
                row["posixOnly"] = list(m["posixOnly"])
                posix_only.append({"g": name, "i": i, "ids": list(m["posixOnly"])})
            if a != "hit":
                key = m.get("key")
                ident = _proof_ident(name, pr)
                if cache is None:
                    row["missWhy"] = "the verdict cache was off"
                elif row.get("u"):
                    row["missWhy"] = "unkeyable: %s" % row["u"]
                elif key and key in run.keys0:
                    row["missWhy"] = ("PROVE-ONCE VIOLATION: banked for these exact bytes before this run began, and "
                                      "run again")
                    violations.append({"g": name, "i": i, "key": str(key)[:16], "a": a})
                elif ident in before:
                    row["missWhy"] = ("banked %s before this run under other bytes - an input, the proof entry, its "
                                      "gate spec or the prover moved" % _age_say(before[ident]))
                else:
                    row["missWhy"] = "never banked on this machine"
            per.append(row)
    return {
        "v": 1, "at": t0_ms, "wallS": round(time.time() - run.t0, 1), "waveS": run.wave_s,
        "gates": sorted(n for n, _f, _p in have), "proofs": n_proofs,
        "forecast": fc, "actual": ac, "unkeyable": unkeyable, "fellThrough": fell,
        "proveOnceViolations": None if cache is None else violations,
        "posixOnlyCatch": posix_only,                  # REG-2357 - each files BLIND on a Windows census (round 4)
        "signalKilled": _SIGNAL_RUNS["n"] - run.sig0,
        "checkpoint": _checkpoint_record(run, per),
        "tracedListing": (None if cache is None else           # REG-2944 - listing laws: banked under v3, or why not
                          {"banked": cache.traced["banked"], "refused": cache.traced["refused"],
                           "why": dict(sorted(cache.traced["why"].items(), key=lambda kv: -kv[1])[:8])}),
        "seams": _heart2_seams(),
        "cache": cache.summary(n_proofs) if cache is not None else "off",
        "stopped": list(run.first) if run.first else None,
        "results": dict(results or {}),
        "perProof": per,
    }


def _checkpoint_record(run, per):
    """#150 - what the checkpoints cost and bought this push, forecast vs actual. -> dict
    forecast: per gate, the proofs forecast to RUN (narrow / full), and the checkpoints that many would ask
    ((n - 1) // CHECKPOINT_EVERY); actual: the clean runs asked and their seconds (the COST), the proofs banked early and
    the seconds of their work (what a kill could no longer lose), the reds and the proofs they took back, and the hits a
    killed run's checkpoint had banked (work actually SAVED). A K that costs more than it saves reads as cost > saved."""
    runs_by_gate = {}
    for r in per:
        if r.get("f") in ("narrow", "full"):
            runs_by_gate[r["g"]] = runs_by_gate.get(r["g"], 0) + 1
    c = dict(getattr(run, "ckpt", None) or {})
    return {"every": CHECKPOINT_EVERY,
            "forecast": sum(max(0, (n - 1) // CHECKPOINT_EVERY) for n in runs_by_gate.values()),
            "runs": int(c.get("runs") or 0), "costS": round(float(c.get("s") or 0), 1),
            "banked": int(c.get("banked") or 0), "bankedS": round(float(c.get("bankedS") or 0), 1),
            "red": int(c.get("red") or 0), "revoked": int(c.get("revoked") or 0),
            "savedHits": int(c.get("resumed") or 0), "savedS": round(float(c.get("resumedS") or 0), 1)}


def _decided_before_a_run(sandbox, name, filename, pr, idx):
    """REG-2353 (round 4) — the verdict a push-time proof reaches before ANY run of it, or None when it will run.
    -> ELSEWHERE (it needs what this PC lacks) | INVALID (an undeclared need, a law whose every case skips off POSIX
    with no such need declared, a target outside the sandbox, widths nobody can read) | UNPROVABLE (its target or its
    PROOF_NEEDS subject is not here, or that declaration cannot be read) | None

    Asked of _prove_one ITSELF (dry: every door before its first run, and nothing after), and of the widths rule
    _prove_push_one_run applies first - one set of doors, so the forecast and the push cannot part. Never raises: a
    door that raises here answers None and the proof is priced as the run it may well be."""
    try:
        if isinstance(pr, dict) and "widths" in pr:
            import law_widths as _LW
            try:
                _LW.declared(pr)
            except ValueError:
                return INVALID
        return _prove_one(sandbox, name, filename, pr, idx, lambda *a, **k: None, why={}, dry=True)
    except Exception:
        return None


def _proof_path(cache, sandbox, name, filename, pr, idx):
    """REG-2353 — the path one push-time proof will take, judged with the run's own primitives before any run of it.
    -> (path: "hit" | "narrow" | "full" | "none", why it cannot be banked | None, the verdict it reaches without a run
    | None)

    hit: the verdict cache would serve its key (key_for + peek - lookup's own predicate, as _prove_push_one asks it);
    none (round 4): it is decided before any run - ELSEWHERE, INVALID or UNPROVABLE, by _prove_one's own doors - so it
    is never priced as a run (the push record calls that path none too); narrow: the red memory names the cases that
    caught it and the gate takes case ids (no argv tail, no -c script - _prove_one's rule); full: anything else. With
    the cache off nothing is a hit and nothing is called unkeyable. A forecast MARKS NOTHING: peek and _red_peek, never
    lookup or _red_recall, which record a use."""
    why = None
    if cache is not None:
        try:
            key, _rels, why = cache.key_for(sandbox, name, filename, pr)
        except Exception as _ke:
            key, why = None, "taking its key raised %s (%s)" % (type(_ke).__name__, str(_ke)[:80])
        if key is not None and cache.peek(key) is not None:
            return "hit", None, None
        if key is None and not why:
            why = "no key could be taken"
    _decided = _decided_before_a_run(sandbox, name, filename, pr, idx)  # FORECAST-ASKS-THE-DOORS
    if _decided is not None:
        return "none", why, _decided
    _extra, _to, _script = gate_spec(name)
    if not _extra and not _script and _red_peek(_red_key(name, idx, pr)):
        return "narrow", why, None
    return "full", why, None


def forecast(have, say=print, sandbox=None, cache=None, unmatched=()):
    """REG-2353 (#42 R16) — WHAT A --push RUN OVER `have` WILL DO, said BEFORE any proving. -> dict (never raises)

    One block headed "#42 FORECAST": per law in scope, how many proofs the verdict cache will serve (hit), the red
    memory will narrow, and will run in full; how many are decided before any run (round 4: ELSEWHERE, INVALID or
    UNPROVABLE by _prove_one's own doors - never priced as a run, and `none` in the push record too); how many can never
    be banked and why (UNKEYABLE); the runs that costs and, where gate_costs.json measured the gate, the seconds.
    Judged on a sandbox of the tree with the run's own key and lookup's own predicate (peek), so a forecast hit is
    exactly what the push will reuse - and nothing it asks is marked
    used, in the verdict cache or the red memory (_proof_path). `sandbox` and `cache` are a caller's (a law's
    fixture); left None, a sandbox is built here and dropped, and the cache is opened read-only (HEART2_PROVE_CACHE=0
    honoured). Anything that goes wrong prints UNKNOWN and returns - a forecast never refuses a push."""
    out = {"proofs": sum(len(p or []) for _n, _f, p in have), "hit": 0, "narrow": 0, "full": 0, "none": 0,
           "unkeyable": 0, "laws": [], "why": None}
    for _un, _uwhy in (unmatched or ()):
        say("  #42 FORECAST: %r %s - nothing will be proven for it (REG-2352)" % (_un, _uwhy))
    _own = None
    _quiet = lambda *a, **k: None                       # noqa: E731
    try:
        if not have:
            out["why"] = "no named gate declares a red-proof"
            say("  #42 FORECAST — nothing in scope: %s" % out["why"])
            return out
        if cache is None:
            cache = open_cache(say=_quiet)
        if sandbox is None:
            sandbox, _own = make_sandbox(say=_quiet)
            if not sandbox:
                out["why"] = "no sandbox could be built to take the keys on"
                say("  #42 FORECAST: UNKNOWN - %s" % out["why"])
                return out
        try:
            import self_prove as _sp
            costs = _sp._gate_costs() or {}
        except Exception:
            costs = {}
        for name, filename, proofs in have:
            row = {"gate": name, "proofs": len(proofs or []), "hit": 0, "narrow": 0, "full": 0, "none": 0,
                   "decided": {}, "unkeyable": 0, "why": None}
            try:
                for i, pr in enumerate(proofs or []):
                    path, why, decided = _proof_path(cache, sandbox, name, filename, pr, i)
                    row[path] += 1
                    if decided:                          # REG-2353 (round 4) - decided before any run: never priced
                        row["decided"][decided] = row["decided"].get(decided, 0) + 1
                    if why:
                        row["unkeyable"] += 1
                        row["why"] = row["why"] or str(why)[:140]
            except Exception as _fe:
                row["unknown"] = "%s: %s" % (type(_fe).__name__, str(_fe)[:80])
            # runs: a narrowed proof asks its cases twice (untampered, tampered); a full one tampers once, and a gate with
            # any full proof adds its shared clean run and its closing run. Seconds price only the FULL runs, at the
            # gate's measured cost per run - a narrowed subset's time is not measured anywhere, so it is not guessed. A
            # proof decided before any run (none: ELSEWHERE, INVALID, UNPROVABLE) costs no run at all.
            _full_runs = row["full"] + (2 if row["full"] else 0)
            row["runs"] = 2 * row["narrow"] + _full_runs
            try:
                row["seconds"] = int(round(float(costs.get(name)) * _full_runs))
            except (TypeError, ValueError):
                row["seconds"] = None
            out["laws"].append(row)
            for k in ("hit", "narrow", "full", "none", "unkeyable"):
                out[k] += row[k]
        _secs = [r["seconds"] for r in out["laws"] if r.get("seconds") is not None]
        say("  #42 FORECAST — %d law(s), %d proof(s) in scope: %d hit · %d narrow · %d full · %d decided before any run"
            " · %d UNKEYABLE (never banked) · ~%d run(s)%s%s"
            % (len(out["laws"]), out["proofs"], out["hit"], out["narrow"], out["full"], out["none"], out["unkeyable"],
               sum(r["runs"] for r in out["laws"]),
               (", ~%dm of full runs where measured" % (sum(_secs) // 60)) if _secs else "",
               "" if cache is not None else " - the verdict cache is OFF, so nothing is a hit"))
        for r in out["laws"]:
            if r.get("unknown"):
                say("     %-52s UNKNOWN - %s" % (r["gate"], r["unknown"]))
                continue
            parts = ["%d %s" % (r[k], k) for k in ("hit", "narrow", "full") if r[k]]
            if r["none"]:
                parts.append("%d decided before any run (%s)" % (r["none"], ", ".join(
                    "%d %s" % (n, v) for v, n in sorted(r["decided"].items()))))
            say("     %-52s %3d proof(s): %s%s · ~%d run(s)%s" % (
                r["gate"], r["proofs"], " · ".join(parts) or "none",
                (" · %d UNKEYABLE - %s" % (r["unkeyable"], r["why"])) if r["unkeyable"] else "", r["runs"],
                (" (~%ds of full runs)" % r["seconds"]) if r.get("seconds") else ""))
        return out
    except Exception as _e:
        out["why"] = "%s: %s" % (type(_e).__name__, str(_e)[:120])
        say("  #42 FORECAST: UNKNOWN - the forecast itself failed (%s); the push decides as it always has" % out["why"])
        return out
    finally:
        if _own:
            _drop_sandbox(_own)


#: REG-2585 — this run's proof shard (main() sets it from --proof-shard K/N; None everywhere else). One prover per process.
_SHARD = {"spec": None, "manifest": None}


def _push_browser(have, unk=None):
    """#42 - the gates a push run proves one at a time: those whose import closure reaches a browser, and those that
    declare widths. ONE rule for the run's lock and for the shard plan (REG-2593), so the two never disagree. -> set"""
    return browser_gates([(n, f) for n, f, _p in have], unclassified=unk) | set(
        n for n, _f, p in have if _declares_widths(p))


def _guards_first(gates, have, say=None):
    """v3889 (#103/#44, the river on every PC) - a shard proves the laws that guard a LOCK first, the rest after, each group
    in the run's own order. -> gates, reordered (unchanged when the locks cannot be asked)

    MEASURED 11-09 on the work ALT (SSH, read-only): its v3888 import was GitHub's Windows set, PARTIAL - 3,496 proofs cut
    at the shards' 55-minute deadline, the make-up round too (shard 15: test_a_pruned_frame_says_it_was_pruned "26
    proof(s) cut at their bound") - so frame.release, vault.sweep_start and vault.apply stayed shut on every Windows PC
    ("6 of its own guard law(s) changed or are unproven"), and its own prover, starved beside the Boosteroid stream, could
    not fill them. A deadline cuts what has not STARTED, so the order decides what a partial set holds: 315 of 1,713 gates
    guard a lock (self_arming's own rule, _lock_guard - the one the PC's prover ranks by, #103-C), and they go first.
    The plan (which proofs are this shard's) is unchanged, so the fan-in's one-plan check still holds."""
    try:
        import self_arming as _sa
        files = dict((n, f) for n, f, _p in have)
        guard = set(n for n in gates for lk in _sa.LOCK_DOORS if _sa._lock_guard(n, lk, files))
    except Exception as _e:
        if say:
            say("  v3889 GUARDS FIRST: the locks could not be asked (%s) - this shard keeps the run's order" % type(_e).__name__)
        return gates
    out = [g for g in gates if g in guard] + [g for g in gates if g not in guard]
    if say:
        say("  v3889 GUARDS FIRST: %d of this shard's %d gate(s) guard a lock and are proved first" % (len(guard), len(gates)))
    return out


def _shard_cut(have, order, gates, say):
    """REG-2585 — a push run cut down to its proof shard. -> (order, gates); unchanged when no shard is set.

    Every shard computes the SAME plan (proof_shard.plan over `have` and gate_costs.json) and keeps only its own proofs,
    in the run's order; a gate with no proof here is not run at all - not even its clean run."""
    spec = _SHARD.get("spec")
    if not spec:
        return order, gates
    import proof_shard as _PS
    k, n = spec
    # REG-2593 - priced by what a proof MEASURED on a runner, and balanced on the browser queue too (it runs serially)
    _rep = {}
    assignment = _PS.plan(have, n, _PS.gate_costs(), browser=_push_browser(have), per_proof=_PS.proof_costs(),
                          served=_SHARD.get("served"), report=_rep)     # REG-3211 - the owed work decides, not the names
    own = _PS.mine(assignment, k)
    order2, gates2 = _PS.restrict_order(order, gates, own)
    gates2 = _guards_first(gates2, have, say)    # v3889 (#103/#44) - a deadline cut never lands on a lock's guard first
    order2 = dict((g, order2[g]) for g in gates2)   # the tamper wave walks this dict: the same order as the clean wave
    _SHARD["plan"] = _PS.plan_digest(have, n, assignment)
    _SHARD["own"] = own
    say("  REG-2585 PROOF SHARD %d/%d: %d of %d proof(s) in %d gate(s) are this shard's (plan %s); the rest are the "
        "other shards' and are NOT RUN here" % (k, n, sum(len(v) for v in order2.values()),
                                                sum(len(p) for _n, _f, p in have), len(gates2), _SHARD["plan"][:12]))
    _w = _rep.get("wall") or []
    say("  REG-3211 OWED-WORK PLAN: %s; this shard's modelled wall %s s, the slowest shard's %s s, the mean %s s"
        % ("the bank holds %d of %d proof(s) PROVEN at this exact commit, %d are owed and spread longest-first"
           % (_rep.get("served", 0), _rep.get("served", 0) + _rep.get("owed", 0), _rep.get("owed", 0))
           if _SHARD.get("served") is not None else "no served list for this commit, so every proof is priced as owed",
           ("%.0f" % _w[k - 1]) if len(_w) >= k else "UNKNOWN", ("%.0f" % max(_w)) if _w else "UNKNOWN",
           ("%.0f" % (sum(_w) / len(_w))) if _w else "UNKNOWN"))
    # REG-3273 - the plan says whether its slowest shard fits the proving window with room, before the round finds out
    say("  REG-3273 HEADROOM: %s" % _PS.headroom(_w)[1] if _w else "  REG-3273 HEADROOM: UNKNOWN - the plan said no wall")
    return order2, gates2


def plan_shards(target_s=None, n_min=None, n_max=None, fallback=22, output=None, say=print):
    """v3891 (#194, his 11-09: "optimize the #194 all the way and make sure it keeps getting faster self improve it") - HOW
    MANY SHARDS THIS COMMIT NEEDS. The seed job asks before any shard starts: every declaring gate (prove()'s own scope
    with nothing named), the seed's served list and carried prices (the same HEART2_SHARD_SERVED / HEART2_SHARD_COSTS the
    shards read), and proof_shard.choose_n over _shard_cut's own plan arguments - so the count is cut by the model every
    shard plans from. A plan that cannot be cut is never a red round: it says why and answers `fallback`.
    -> 0 always; prints and (output) appends `n=` and `list=` for the workflow's matrix."""
    import proof_shard as _PS
    kw = {}
    if target_s:
        kw["target_s"] = float(target_s)
    if n_min:
        kw["n_min"] = int(n_min)
    if n_max:
        kw["n_max"] = int(n_max)
    try:
        gates = gate_files(say=lambda *_a, **_k: None)
        have = [(n, f, p) for n, f, p in ((n, f, red_proofs_in(f)) for n, f in gates_named(None, gates)) if p]
        served = _served_now(have, say=say)
        n, info = _PS.choose_n(have, costs=_PS.gate_costs(), browser=_push_browser(have), per_proof=_PS.proof_costs(),
                               served=served, **kw)
        why = info.get("why")
        say("  v3891 (#194) SHARD COUNT: %d - %s (owed %s, served %s, %d gate(s) declare proofs)"
            % (n, why, info.get("owed"), info.get("served"), len(have)))
    except Exception as e:
        n = max(1, int(fallback or 22))
        say("  v3891 (#194) SHARD COUNT: %d - the plan could not be cut (%s: %s), so the round runs at the default"
            % (n, type(e).__name__, str(e)[:160]))
    lines = "n=%d\nlist=%s\n" % (n, json.dumps(list(range(1, n + 1)), separators=(",", ":")))
    sys.stdout.write(lines)
    if output:
        try:
            with io.open(output, "a", encoding="utf-8") as fh:
                fh.write(lines)
        except OSError as e:
            say("  v3891 (#194): the count could not be written to %s (%s)" % (output, type(e).__name__))
    return 0


def _served_now(have, path=None, head=None, say=None):
    """REG-3211 - {(gate, index)} the proof bank already holds PROVEN for THIS exact commit: the seed job's served.json
    (HEART2_SHARD_SERVED), the identities of every servable PROVEN in the commit's own bundle (tv/proof_seed.py). Every
    shard reads the same file (the seed job's one artifact, its sha256 checked), so every shard cuts the same plan. It
    prices the plan only - what is served is still decided proof by proof by peek() under THIS checkout's key, so a hint
    that is wrong costs balance, never a verdict. Not a key per proof here: MEASURED on his Mac (nice 10, load ~12),
    keying 466 proofs of 60 gates took 81 s - ~25 minutes for the census's 8,847 - which every shard would pay first.
    -> set | None (no hint, or one for another commit: UNKNOWN - every proof is priced as owed, as before REG-3211)"""
    path = path if path is not None else (os.environ.get("HEART2_SHARD_SERVED") or "")
    say = say or (lambda *a, **k: None)
    if not path:
        return None
    try:
        with io.open(path, encoding="utf-8") as fh:
            body = json.load(fh)
        rows = body.get("served") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            raise ValueError("no served list")
    except (OSError, ValueError) as e:
        say("  REG-3211: the seed's served list %s is unreadable (%s) - every proof is priced as owed"
            % (os.path.basename(path), type(e).__name__))
        return None
    if head is None:
        ok, h = _git("rev-parse", "HEAD")
        head = h.strip() if ok else ""
    if not head or body.get("sha") != head:
        say("  REG-3211: the seed's served list is for %s, not this checkout's HEAD %s - every proof is priced as owed"
            % (str(body.get("sha"))[:12], str(head)[:12] or "UNKNOWN"))
        return None
    have_ids = set((str(n), i) for n, _f, p in have for i in range(len(p or [])))
    return set((str(r[0]), r[1]) for r in rows
               if isinstance(r, list) and len(r) == 2 and type(r[1]) is int and (str(r[0]), r[1]) in have_ids)


def _shard_finish(cache, names, stopped, say):
    """REG-2585 — a FINISHED shard writes its manifest into its own cache file, through the store's one writer.
    -> True when written. Never called for a run that could not prove (no sandbox): an unfinished shard has none."""
    spec = _SHARD.get("spec")
    if not spec or cache is None:
        return False
    import proof_shard as _PS
    ok_h, head = _git("rev-parse", "HEAD")
    ok_d, dirty = _tracked_dirty()
    # REG-2591 - a shard keeps going, so it never STOPS: every failure it found is OWED (stopped stays None)
    m = _PS.manifest(spec[0], spec[1], head.strip() if ok_h else "", (bool(dirty.strip()) if ok_d else True),
                     _SHARD.get("plan") or "", _SHARD.get("own") or {}, names, None,
                     int(time.time() * 1000), owed=stopped)
    cache.flush()

    def merge(disk):
        body = dict(disk or {})
        body.setdefault("format", 2)
        body.setdefault("entries", {})
        body["shard"] = m
        return body
    ok, why = cache.file.commit(merge)
    say("  REG-2585 PROOF SHARD %d/%d: %s" % (spec[0], spec[1], "manifest written (head %s%s)" % (
        m["head"][:12], ", DIRTY - an import will refuse it" if m["dirty"] else "") if ok
        else "the manifest could NOT be written (%s) - an import will refuse this shard" % why))
    _SHARD["manifest"] = m if ok else None
    return ok


def _owe_all(run, per_proof, say, stopped):
    """REG-2591 - the end of a kept-going shard: say every failure it OWES, and hand them all to main (which exits red)
    and to the manifest (`owed`). Never one only: a shard that kept going found them all."""
    _unrun = sum(1 for _p in (per_proof or {}).values() for x in _p if x is None)
    _gates = sorted(set(f[0] for f in run.failures))
    say("")
    say("  ⚠ REG-2591 SHARD KEPT GOING: %d failure(s) in %d gate(s) are OWED a fix; %d proof(s) NOT RUN (only the "
        "failed gates' own). Every other gate ran. The shard is red on these:" % (len(run.failures), len(_gates), _unrun))
    for _n, _i, _v, _why in run.failures:
        say("     OWED %s[%d] %s — %s. Reproduce: python3 tv/heart2.py --prove %s --push" % (_n, _i, _v, _why, _n))
    if stopped is not None:
        stopped.extend(run.failures)


def _prove_push(have, say, stopped=None, cache=None, blank=None):
    """#42 — prove() at push time. -> ({name: verdict}, {name: [verdict | None]}) | (None, None); NOT_RUN gates are left
    OUT of the verdicts (never banked), and a stop is appended to `stopped` for main() to refuse on.
    `cache` (P3) is the _VerdictCache prove(push=True) opened; None - every other caller - runs every proof."""
    global _PUSH
    _nw = sum(1 for _n, _f, _p in have for _pr in _p if isinstance(_pr, dict) and "widths" in _pr)
    _np = sum(len(_p) for _n, _f, _p in have)
    say("  #42 PUSH TIME: %d of %d proof(s) declare the widths their defect shows at and run only there; the other %d "
        "run at every width. The full sweep stays run_gates' and CI's." % (_nw, _np, _np - _nw))
    _seams = _heart2_seams()
    say("  #42 SEAMS (REG-2352): %s" % (" · ".join("%s=%s" % kv for kv in _seams.items()) if _seams else
                                        "no HEART2_* variable is set - every default holds"))
    base, order, gates, counts = _push_facts(have, say)
    _SHARD["served"] = _served_now(have, say=say) if _SHARD.get("spec") else None   # REG-3211 - what is still owed
    order, gates = _shard_cut(have, order, gates, say)                 # REG-2585 - only this shard's proofs
    _keep = bool(_SHARD.get("spec"))                                   # REG-2591 - a CI shard keeps going
    say("  #42 FAIL FAST: likeliest to fail first - %d anchor(s) off, %d entr(ies) new or changed since %s, %d whose "
        "tampered file changed; %s."
        % (counts["anchor"], counts["entry"], base or "an UNKNOWN base (neither @{push} nor origin/main resolves - "
           "nothing ranks as changed)", counts["target"],
           "REG-2591 SHARD MODE: a BLIND / INVALID / clean-run red is OWED and the shard keeps going" if _keep else
           "the run stops at the first BLIND / INVALID / clean-run red"))
    # the import CLOSURE, not the gate's own imports: a gate that starts Chrome through a helper holds the lock too
    _unk = []
    browser = _push_browser(have, _unk)
    if browser:
        say("  #42 ONE BROWSER AT A TIME: %d gate(s) reach a browser through their imports (any depth) and are proved "
            "one after another: %s" % (len(browser), ", ".join(sorted(browser)[:6]) + (" …" if len(browser) > 6 else "")))
    if _unk:
        say("  #42 ⚠ %d gate(s) import a file nobody could read or parse, so whether they start a browser is UNKNOWN - "
            "they hold the lock too: %s" % (len(_unk), ", ".join(sorted(_unk)[:6])))
    by = dict((n, (n, f, p)) for n, f, p in have)
    run = _PushRun(order, browser, cache, keep_going=_keep)
    try:
        run.direct = _direct_laws(have, _push_changed()[1])     # REG-2599 - who still owes a clean run here
    except Exception as _de:
        say("  ⚠ REG-2599 which laws this push changes could not be read (%s) - every gate served from another tree "
            "owes a clean run here, as before" % type(_de).__name__)
    if run.direct is not None:
        say("  REG-2599: %d of %d gate(s) have their own law file changed by this push - only those owe a clean run here "
            "for a proof another tree banked" % (len(run.direct), len(have)))
    _prev, _PUSH = _PUSH, run
    try:
        # REG-1992 — THE CLEAN WAVE FIRST: every gate's one untampered run, across the lanes, before any tamper
        # Only when gates outnumber lanes: with as many lanes as gates, every gate's first clean run already starts
        # at the run's first second, and a wave would only add a run.
        _lanes = prove_workers(len(gates))
        _wave = _wave_owed(gates, by, run) if len(gates) > _lanes else []   # REG-2631 - only what the wave would run
        if len(gates) > _lanes and not _wave:
            say("  REG-2631 CLEAN WAVE SKIPPED: every proof of all %d gate(s) is served from the cache on this tree's "
                "own keys and none owes a clean run here, so the wave would build its lanes to run nothing" % len(gates))
        elif len(gates) > _lanes:
            _w0 = time.time()
            say("  REG-1992 CLEAN WAVE: %d gate(s) over %d lane(s) - every gate's untampered run first, so a law "
                "already red refuses in minutes%s" % (len(_wave), _lanes, (" (REG-2631: %d gate(s) served whole from "
                "the cache are left out)" % (len(gates) - len(_wave))) if len(_wave) < len(gates) else ""))
            run.wave = True
            try:
                _prove_gates([by[n] for n in _wave], say, blank=set())
            finally:
                run.wave = False
                run._items = None              # take() drains the main pass's own queue
            run.wave_s = round(time.time() - _w0, 1)       # REG-2353 - the push record keeps the wave's minutes
            say("  REG-1992 CLEAN WAVE: %d clean run(s) measured in %.0f s%s"
                % (len(run.clean_wave), time.time() - _w0,
                   " - STOPPED on a red" if run.stop.is_set() else " - all green"))
        if run.stop.is_set():
            results = dict((n, NOT_RUN) for n in gates)
            per_proof = dict((n, [None] * len(by[n][2])) for n in gates)
        else:
            results, per_proof = _prove_gates([by[n] for n in gates], say, blank=blank)
    finally:
        _PUSH = _prev
    if cache is not None:
        cache.flush()
        say("  " + cache.summary(_np))
    try:                                               # REG-2353 - a record that cannot be built costs a line, never a push
        _PUSH_RECORD["record"] = _push_record(run, have, cache, _np, results)
        _r = _PUSH_RECORD["record"]
        say("  #42 RECORD (REG-2353): forecast %d hit · %d narrow · %d full; actual %d hit · %d narrow · %d full · %d "
            "not run · %d fell through; %s prove-once violation(s); %d run(s) a signal ended; %d proof(s) caught only "
            "off POSIX (REG-2357)"
            % (_r["forecast"]["hit"], _r["forecast"]["narrow"], _r["forecast"]["full"], _r["actual"]["hit"],
               _r["actual"]["narrow"], _r["actual"]["full"], _r["actual"]["notRun"], _r["fellThrough"],
               "UNKNOWN (the cache was off)" if _r["proveOnceViolations"] is None else len(_r["proveOnceViolations"]),
               _r["signalKilled"], len(_r["posixOnlyCatch"])))
        _c = _r.get("checkpoint") or {}
        say("  #42 RECORD #150 checkpoints (every %d): forecast %d, ran %d costing %.0f s; banked %d proof(s) early (%.0f s "
            "of work a kill could no longer lose), %d red took back %d; SAVED: %d hit(s) a killed run's checkpoint "
            "banked (%.0f s)" % (_c.get("every", CHECKPOINT_EVERY), _c.get("forecast", 0), _c.get("runs", 0),
                                 _c.get("costS", 0), _c.get("banked", 0), _c.get("bankedS", 0), _c.get("red", 0),
                                 _c.get("revoked", 0), _c.get("savedHits", 0), _c.get("savedS", 0)))
        _tl = _r.get("tracedListing")
        if _tl is not None:
            say("  #42 RECORD REG-2944 listing laws: %d PROVEN(s) banked under what their traced run listed, %d not "
                "banked%s" % (_tl["banked"], _tl["refused"],
                              (" - " + "; ".join("%s x%d" % kv for kv in list(_tl["why"].items())[:3])) if _tl["why"]
                              else ""))
        _tw = _trace_why_census()
        if _tw is not None:
            say("  #42 RECORD REG-3319 trace: %d of %d law file(s) this run traced completely - their PROVENs may be keyed "
                "by name; the rest keep every byte%s" % (_tw["ok"], _tw["laws"],
                                                         (" - not traced because: " + "; ".join(
                                                             "%s x%d" % kv for kv in _tw["causes"][:6])) if _tw["causes"]
                                                         else ""))
        for _v in (_r["proveOnceViolations"] or [])[:6]:
            say("     ⚠ PROVE-ONCE VIOLATION: %s[%d] was banked for these exact bytes before this run began and ran "
                "again (%s)" % (_v["g"], _v["i"], _v["a"]))
        for _v in _r["posixOnlyCatch"][:6]:
            say("     ⚠ REG-2357: %s[%d] was caught only by case(s) that skip off POSIX (%s): it files BLIND on every "
                "Windows census - declare \"needs\": \"posix\"" % (_v["g"], _v["i"], ", ".join(_v["ids"][:3])))
    except Exception as _re:
        _PUSH_RECORD["record"] = None
        say("  #42 RECORD (REG-2353): could not be built (%s: %s) - UNKNOWN, the run's verdicts stand"
            % (type(_re).__name__, str(_re)[:80]))
    if results is None:
        return None, None
    not_run = sorted(n for n, v in results.items() if v == NOT_RUN)
    results = dict((n, v) for n, v in results.items() if v != NOT_RUN)
    if cache is not None:
        # ⚠ A REUSED PROOF KEEPS THE TIME IT WAS MEASURED. A PROVEN gate standing on any cached proof is only as fresh
        # as the OLDEST of them (a proof that ran now is newer than any entry), so the census stamps that gate with
        # that time and not this run's clock. Only PROVEN: a BLIND / INVALID / UNPROVABLE came from a proof that RAN.
        # prove() reads cache.measured and hands it to _write_state. [[stale-reading]] [[inherited-claim-is-not-evidence]]
        _ages = _reused_ages(cache, results)
        cache.measured = _ages
        if _ages:
            say("  #42 P3 CACHE: %d gate(s) stand on reused proofs, so the census keeps the age each was MEASURED at "
                "(oldest %s ago), never this run's clock" % (len(_ages), _age_say(min(_ages.values()))))
    if run.keep_going and run.failures:
        _owe_all(run, per_proof, say, stopped)
    elif run.first:
        _n, _i, _v, _why = run.first
        _unrun = sum(1 for _p in per_proof.values() for x in _p if x is None)
        say("")
        say("  ⛔ #42 STOPPED at the first failure: %s[%d] %s — %s." % (_n, _i, _v, _why))
        say("     %d of %d proof(s) NOT RUN%s. Nothing unrun is banked or passed: the push is refused on the failure "
            "above. Reproduce: python3 tv/heart2.py --prove %s --push" % (
                _unrun, _np, (" (%d gate(s) never started: %s)" % (len(not_run), ", ".join(not_run[:6])))
                if not_run else "", _n))
        if stopped is not None:
            stopped.append(run.first)
    return results, per_proof


def _reused_ages(cache, results):
    """⚠ A REUSED PROOF KEEPS THE TIME IT WAS MEASURED - the push's rule, and (#186) the census's: a PROVEN gate standing on
    any cached proof is only as fresh as the OLDEST of them. -> {gate: oldest provedAt ms}; {} with no cache"""
    _ages = {}
    if cache is not None:
        for (_gn, _i), _ms in list(cache.reused.items()):
            if results.get(_gn) == PROVEN:
                _ages[_gn] = min(_ages[_gn], _ms) if _gn in _ages else _ms
    return _ages


#: #186 - the verdict cache the self-prove lane's census serves and banks through. prove(reuse=True) opens it; None means
#: every proof runs - the verdict of record (run_gates, CI, a hand --prove) never opens it.
#: REG-3191: "here" - the gates this census judges on this PC whatever another tree banked (the environment self-check, or
#: every gate of a safety-net run); REG-3192: "red" - the gates whose clean run went RED here this run.
_CENSUS = {"cache": None, "here": (), "red": set(), "net": False}


def _census_cache(reuse, say=print):
    """#186 (his ruling 2026-10-28: "NO IT DOESNT NEED TO PROVE ITSELF. it can accept a proof earned on byte identical ...
    it should work with that same recipe") - the cache a census opens. -> _VerdictCache | None

    Only the self-prove lane asks (`heart2.py --prove ... --reuse`): its census serves a PROVEN banked over byte-identical
    inputs - the push's own key, the push's own lookup - and banks what it proves, so the proofs a push banked make this
    PC's census current without re-running them, and a slice that stands aside keeps what it proved. A served proof is
    kept on the banking tree's word with no clean run here: REG-2599's rule (a run that changes no law owes none) and his
    ruling above. HEART2_PROVE_CACHE=0 closes it, said. A cache that will not open costs a re-prove, never a verdict."""
    if not reuse:
        return None
    if _prove_cache_off():
        say("  #186 CENSUS CACHE: OFF for this run (HEART2_PROVE_CACHE=0) - every proof runs, nothing is banked")
        return None
    try:
        c = _VerdictCache(say=say)
    except Exception as _ce:
        say("  #186 CENSUS CACHE: could not be opened (%s) - every proof runs, nothing is banked" % type(_ce).__name__)
        return None
    say("  #186 CENSUS CACHE: a PROVEN banked over byte-identical inputs is served, not re-run; what this census proves "
        "is banked (%d entr(ies) on this PC)" % len(c.entries))
    return c


def _census_one(sandbox, name, filename, pr, idx, say):
    """#186 - ONE census proof: served from the cache over byte-identical inputs (_cache_serve, the push's rule), else run
    as the census always ran it (_prove_one, the whole law) and banked (_cache_bank) once its gate's closing clean run
    has kept it PROVEN. A proof that declares a need this PC lacks - or whose need cannot be probed - is never served:
    it is judged here exactly as before, whatever another PC banked. -> verdict"""
    cache = _CENSUS.get("cache")
    # a proof whose declared need this PC lacks is never served: _cache_serve holds that for both callers (REG-3118)
    if cache is None:
        return _prove_one(sandbox, name, filename, pr, idx, say)
    try:
        served, key, rels = _cache_serve(cache, sandbox, name, filename, pr, idx, say)
    except Exception as _se:
        # the cache may cost a re-prove, never a verdict: a raise here would file the proof BLIND (_prove_gate_proofs),
        # and one BLIND shuts every lock on this PC - so it runs, unbanked, as with no cache at all
        say("     %-52s   ↳ #186: the census cache raised %s - this proof runs and is not banked"
            % ("%s[%d]" % (name, idx), type(_se).__name__))
        return _prove_one(sandbox, name, filename, pr, idx, say)
    if served is not None:
        return served
    v = _prove_one(sandbox, name, filename, pr, idx, say)
    _cache_bank(cache, sandbox, name, filename, pr, idx, say, key, rels, v, by="census")
    return v


def _census_bank(cache, name, per, say):
    """#186 - after the gate's closing clean run (REG-1669 / REG-1988): each pending PROVEN that is STILL PROVEN is banked -
    the same _bankable rule and deferred v2 key _prove_gate_push's loop applies - and the gate's bank reaches the disk now,
    per gate, so a slice that stands aside keeps it. -> how many were banked"""
    n = 0
    for _i, _key, _entry in (getattr(_CLEAN, "pending", None) or []):
        if _bankable(per[_i]):
            if callable(_key):
                _key = _key()
            if _key is None:                         # REG-2944 - a listing law whose trace cannot key it
                cache.count("moved")
                continue
            cache.store(_key, _entry)
            cache.count("stores")
            n += 1
        else:
            cache.count("moved")
            say("     %-52s   ↳ #186: not banked - the gate's closing clean run took its PROVEN away"
                % ("%s[%d]" % (name, _i)))
    cache.flush()
    return n


def _census_locked():
    """REG-3191 - THE CENSUS'S ONE LOCK: every read-merge-write of the census holds it, across processes. -> a context

    The census had one writer at a time by habit (the lane's slice, a push, a hand --prove). REG-3191 adds writers that
    run beside a slice - the trust pass right after an import, the lane's own trust run - and a census write is a read,
    a merge and a replace: one landing between another's read and replace was lost, and a lost write can be a BLIND
    (the next slice bank wrote it back, a minute later). The stores' own lock, on the census's directory."""
    return _store_locked(os.path.dirname(os.path.abspath(STATE)))


def _under_census_lock(fn):
    """REG-3191 - a census writer that holds _census_locked for its whole read-merge-write. `.unlocked` is the writer
    itself, for a caller that already holds the lock (the trust pass re-reads the census under it before it writes);
    the lock is not re-entrant. -> the wrapped writer"""
    import functools as _ft

    @_ft.wraps(fn)
    def locked(*a, **k):
        with _census_locked():
            return fn(*a, **k)
    locked.unlocked = fn
    return locked


# ══ REG-3191 / REG-3192 (his ruling 2026-11-05, items 3 and 4) - IMPORTED PROOFS OPEN THE LOCKS; THE FULL PROOF IS A NET ══
# His words ~09:05: "(3) Each PC imports the proofs for byte-identical files at update ... and runs only an environment
# self-check: the laws whose `needs` are platform-specific. Locks open on (imported proofs + local self-check)." ~09:15:
# "(4) the background full proof keeps running at idle as a SAFETY NET but no longer holds the river shut - a red/blind it
# finds goes to the fleet + BUGS and closes only the lock its law guards."
# MEASURED on his Mac (v3864, 2026-11-05 ~21:03): GitHub's 2,928 proofs imported by ~20:55, yet the census owed 162 gates
# and frame.release stayed shut on 17 of its guards. The slice path already SERVES an imported proof (#186 - _census_one
# asks no tree; the live lane's last slice served 183 of 251), so the hold was not a refusal: an owed gate is written into
# the census only when a 40-gate slice reaches it, and the slices queue behind laws that really run (Chrome ones too).
# trust_pass writes, with NO run, every owed gate whose every proof the bank serves over this checkout's own bytes -
# BEFORE the slice proves anything - so a lock waits only on the gates the bank cannot serve and on the environment
# self-check. Those stay owed exactly as before. The push path (_PUSH, REG-2599/REG-2587) never asks any of this.
#: REG-3191 - THE ENVIRONMENT SELF-CHECK, DECLARED (his 2026-10-22 rule: lists are declared, never inferred from source).
#: A gate named here, or one any proof of which declares "needs" (REG-1686), is never written on another tree's word: its
#: foreign proofs are judged on this PC. Seeded only with laws a measured environment find NAMES as its catcher:
#:   REG-3131 (the cp1255 / ANSI codepage)    test_a_windows_console_runs_in_utf8_mode
#:   REG-3152 (chrome.exe --version opens one) test_d2jsp_desk
#:   REG-3151 (his real idle clock)            test_triage_runs_beside_a_shadow_reel
#:   REG-3145 (a push alive on this PC)        test_a_proof_stands_aside_for_a_push
#:   REG-3135 (a shallow checkout's history)   test_a_version_stamp_is_not_a_page_change
#:   REG-3132 (no /tmp on Windows: "the guard is the six laws themselves on every Windows PC's census")
#: REG-3133's POSIX-only premises are here already: every proof only those cases catch declares needs posix(-signals).
#: NOT seeded (no law found that names itself their catcher): node invisible on PATH, the CRLF checkout, the launcher port.
ENV_SELF_CHECK = (
    "test_a_windows_console_runs_in_utf8_mode",
    "test_d2jsp_desk",
    "test_triage_runs_beside_a_shadow_reel",
    "test_a_proof_stands_aside_for_a_push",
    "test_a_version_stamp_is_not_a_page_change",
    "test_a_reels_whole_life_is_one_work_list",
    "test_the_art_resolver_folds_the_apostrophe",
    "test_the_eye_says_which_family_looked",
    "test_the_missing_wall_shows_the_qlvl",
    "test_the_shadow_vault_tab_dates_the_vault_by_its_own_clock",
    "test_the_shelf_shows_the_four_lanes",
)


def env_gate(name, proofs):
    """REG-3191 - is this gate environment-sensitive BY DECLARATION? -> (bool, why)"""
    if name in ENV_SELF_CHECK:
        return True, "named in ENV_SELF_CHECK"
    needs = sorted(set(str(p.get("needs")) for p in (proofs or ()) if isinstance(p, dict) and p.get("needs")))
    if needs:
        return True, "a proof declares needs %s" % ", ".join(needs)
    return False, ""


def split_owed(owed, proofs_of, key_of, peek, here):
    """REG-3191 - what the bank can say for each owed gate. Pure: every read is a callable a caller hands in.

    owed: [gate]; proofs_of(gate) -> (filename, [proof]); key_of(gate, filename, proof) -> key | None (the key the census
    serve takes over this checkout's bytes); peek(key) -> the servable PROVEN entry | None; here: this tree (TREE_ID).
    -> {"trusted": {gate: n proofs another tree proved}, "servedHere": [gate], "env": {gate: why},
        "unservable": {gate: why}, "ages": {gate: oldest provedAt ms}}
    A gate is trusted only when EVERY proof is served and at least one was proved in another tree; every proof served
    from this tree is servedHere (proved here already); a served gate that is environment-sensitive by declaration is
    env (judged here); one proof without a servable PROVEN over these bytes - no key, a key nobody banked (other bytes,
    no import) - is unservable. The last two stay owed exactly as before."""
    out = {"trusted": {}, "servedHere": [], "env": {}, "unservable": {}, "ages": {}}
    for name in owed:
        try:
            filename, proofs = proofs_of(name)
        except Exception as _pe:
            out["unservable"][name] = "its proofs could not be read (%s)" % type(_pe).__name__
            continue
        if not proofs:
            out["unservable"][name] = "it declares no readable proof"
            continue
        foreign, miss, oldest = 0, None, None
        for i, pr in enumerate(proofs):
            try:
                key = key_of(name, filename, pr)
            except Exception as _ke:
                miss = "proof %d: its key could not be taken (%s)" % (i, type(_ke).__name__)
                break
            if key is None:
                miss = "proof %d is not keyable here" % i
                break
            hit = peek(key)
            if not isinstance(hit, dict):
                miss = "proof %d has no PROVEN banked over these bytes" % i
                break
            if hit.get("tree") != here:
                foreign += 1
            _at = hit.get("provedAt")
            if isinstance(_at, (int, float)) and not isinstance(_at, bool):
                oldest = _at if oldest is None else min(oldest, _at)
        if miss:
            out["unservable"][name] = miss
            continue
        if oldest is not None:
            out["ages"][name] = int(oldest)
        if not foreign:
            out["servedHere"].append(name)
            continue
        _env, _ewhy = env_gate(name, proofs)
        if _env:
            out["env"][name] = _ewhy
            continue
        out["trusted"][name] = foreign
    return out


def trust_pass(cache, say=print, gates=None, state=None, write=True):
    """REG-3191 - write into the census, with no run, every owed gate the bank serves whole over this checkout's bytes.
    -> split_owed's answer plus {"owed": n asked, "written": [gate]}

    Asked by prove() for the self-prove lane's census (--reuse, never --push, never --net) before a slice proves
    anything: what it writes is exactly what the slice's _census_one would serve (the same key, the same peek), only
    without waiting for a slice to reach it. A gate the census holds BLIND is never written on another tree's word - that
    BLIND was measured here (his 2026-09-12 ruling). Each written gate keeps the age it was MEASURED at (the oldest
    provedAt it stands on), never this run's clock, and the census names the ones taken on another tree's word
    (`trusted`), which the safety net (REG-3192) then judges here at idle."""
    gates = gates if gates is not None else gate_files()
    if state is None:
        state = {}
        if os.path.exists(STATE):
            with io.open(STATE, encoding="utf-8") as fh:
                state = json.load(fh)
    # v3862 (item 4) - AN OPEN ENVIRONMENT RE-PROVE IS PROVED WITHOUT THE CACHE: a proof banked under the old environment
    # is not this PC's word now, whoever banked it, so the bank is not asked for anything while one is open
    _er = env_reprove_state(state if isinstance(state, dict) else {}, gates)
    if _er and _er.get("owed"):
        say("  REG-3191 TRUST PASS: not asked - this PC's environment changed (%s) and its re-prove runs without the "
            "cache until it is done" % env_change_words(_er))
        return {"trusted": {}, "servedHere": [], "env": {}, "unservable": {}, "ages": {}, "owed": 0, "written": [],
                "envReprove": True}
    so = slice_owed(gates, state)
    _blind = set(state.get("blind") or []) if isinstance(state, dict) else set()
    owed = [n for n, _k in so.get("owed") or [] if n not in _blind]
    files = dict(gates)

    def _proofs_of(n):
        f = files[n]
        return f, red_proofs_in(f)

    def _key_of(n, f, pr):
        return cache.key_for(HERE, n, f, pr)[0]

    say("  REG-3191 TRUST PASS: asking the bank for %d owed gate(s) - each written only if it serves every proof over "
        "these bytes" % len(owed))
    sp = split_owed(owed, _proofs_of, _key_of, cache.peek, TREE_ID)
    take = sorted(set(sp["trusted"]) | set(sp["servedHere"]))
    sp["owed"], sp["written"] = len(owed), []
    if take and write:
        # the keys were taken outside the lock (a minute of hashing must not hold a slice's bank); UNDER it the census is
        # read again and only a gate it still owes, and does not hold BLIND, is written - a BLIND a slice filed since
        # this pass began is never overwritten on another tree's word
        with _census_locked():
            fresh = {}
            if os.path.exists(STATE):
                with io.open(STATE, encoding="utf-8") as fh:
                    fresh = json.load(fh)
            _still = set(n for n, _k in slice_owed(gates, fresh).get("owed") or [])
            _fb = set(fresh.get("blind") or []) if isinstance(fresh, dict) else set()
            take = [n for n in take if n in _still and n not in _fb]
            if take:
                _write_state.unlocked(dict((n, PROVEN) for n in take),
                                      measured=dict((n, sp["ages"][n]) for n in take if n in sp["ages"]),
                                      stamp=False, trusted=set(sp["trusted"]) & set(take))
        sp["written"] = take
    say("  REG-3191 TRUST PASS: %d owed gate(s) asked; %d written on another tree's proofs over byte-identical inputs "
        "(trusted - the safety net judges them here at idle), %d served whole from this tree's own, %d environment "
        "self-check (judged here), %d the bank cannot serve (proved here as before)"
        % (len(owed), len(sp["trusted"]), len(sp["servedHere"]), len(sp["env"]), len(sp["unservable"])))
    return sp


def trust_now(say=print, only=None):
    """REG-3191 - THE TRUST PASS ON ITS OWN, with no slice and no law run: `heart2.py --trust` (the self-prove lane's light
    start, which waits for no idle machine) and `heart2.py --import-shards FILE... --trust` (right after an import lands,
    so the locks open at update, not when a slice next gets a quiet machine). -> 0 asked (written or not), 2 it raised
    REG-3415 - `only` (gate names): ask the bank for those gates alone - the import's early pass over the shut locks'
    guards, which must not re-key every owed law on a PC that keys under one a second.

    MEASURED on his Mac 2026-11-05 22:14: the lane sat 'busy' for 34 min with 6 of its 27 owed gates fully servable by
    the bank and unwritten - the trust pass ran only inside a slice, and a slice waits for idle. The census cache it opens
    is the slice's own (_census_cache: --reuse's rule, HEART2_PROVE_CACHE=0 closes it)."""
    cache = _census_cache(True, say)
    if cache is None:
        say("  REG-3191 TRUST PASS: not asked - the census cache is closed or would not open; the lane proves as before")
        return 0
    try:
        if only is None:
            trust_pass(cache, say=say)
        else:
            _only = set(only)
            trust_pass(cache, say=say, gates=[(n, f) for n, f in gate_files() if n in _only])
    except Exception as _te:
        say("  ✗ REG-3191 TRUST PASS raised %s (%s) - nothing was written on the bank's word"
            % (type(_te).__name__, str(_te)[:160]))
        return 2
    return 0


#: REG-3192 - how long the safety net waits before it asks a trusted gate AGAIN: one it could not judge here (an UNKNOWN or
#: timed-out run, a lane that never measured it) and one it FOUND failing. A find is re-judged so one flaky red on an
#: unattended PC does not shut a lock until someone edits the law (the shape of the old ALT's 28 days ROUTED); a gate it
#: could not judge stays trusted and is asked again, never dropped from the net for good.
NET_RETRY_S = 6 * 3600
#: v3884 (REG-3436) - a RED find seen ONCE is asked again after an hour, not six. MEASURED on his Mac 11-08: one law
#: (test_a_parallel_proof_is_the_same_proof) went red at 09:09 under my local load, its immediate re-check (REG-3324) ran on
#: the same loaded machine and was red again, and the find then held all nine routes shut for NET_RETRY_S - while the law
#: was green alone minutes later. A red seen twice (the hour's re-ask red too) waits NET_RETRY_S as before; BLIND and
#: INVALID finds, and a record whose count cannot be read, keep NET_RETRY_S.
NET_RETRY_FIRST_S = 3600


def _net_seen_once_red(rec):
    """v3884 (REG-3436) - is this a RED find the net has seen exactly once? -> bool (an unreadable count is not once)"""
    seen = rec.get("seen") if isinstance(rec, dict) else None
    return (isinstance(rec, dict) and rec.get("verdict") == "RED" and isinstance(seen, int) and not isinstance(seen, bool)
            and seen == 1)


def _net_age_ok(rec, now_ms):
    """REG-3192 - may the net ask this gate again? A record with no readable time is asked (never held on a guess)."""
    at = rec.get("at") if isinstance(rec, dict) else None
    if not isinstance(at, (int, float)) or isinstance(at, bool):
        return True
    if _net_seen_once_red(rec) and now_ms - at >= NET_RETRY_FIRST_S * 1000:     # v3884 (REG-3436) - a first red: 1 h
        return True
    return now_ms - at >= NET_RETRY_S * 1000


def net_owed(state, gates=None, now_ms=None):
    """REG-3192 - the trusted gates the SAFETY NET owes a judgement here, against the files on disk. -> [(gate, n)]

    A trusted gate is owed until the net has judged it on this PC: never asked, or asked NET_RETRY_S ago and either not
    judged (netUnjudged) or found failing (netFinds) - both are asked again, never dropped for good."""
    if not isinstance(state, dict) or not isinstance(state.get("trusted"), dict):
        return []
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    gates = gates if gates is not None else gate_files()
    files = dict(gates)
    shas = gate_shas([(n, files[n]) for n in state["trusted"] if n in files])
    rec = state.get("gateShas") if isinstance(state.get("gateShas"), dict) else {}
    finds = state.get("netFinds") if isinstance(state.get("netFinds"), dict) else {}
    unj = state.get("netUnjudged") if isinstance(state.get("netUnjudged"), dict) else {}
    out = []
    for n, sha in sorted(state["trusted"].items()):
        if not (n in files and sha and shas.get(n) == sha and rec.get(n) == sha):
            continue
        if n in finds and not _net_age_ok(finds[n], now_ms):
            continue
        if n in unj and not _net_age_ok(unj[n], now_ms):
            continue
        out.append((n, len(red_proofs_in(files[n]) or [])))
    return out


def net_finds(state, gates=None):
    """REG-3192 - the safety net's finds that still speak for the files on disk. -> {gate: find}

    ONE reader for the lock (self_arming._net_heart) and the lane's status (self_prove): a find whose gate file has
    changed since is moot (the census owes that gate again), and a gate no longer registered has no find."""
    finds = state.get("netFinds") if isinstance(state, dict) else None
    if not isinstance(finds, dict) or not finds:
        return {}
    files = dict(gates if gates is not None else gate_files())
    shas = gate_shas([(n, files[n]) for n in finds if n in files])
    return dict((n, f) for n, f in finds.items()
                if isinstance(f, dict) and n in files and f.get("sha") and shas.get(n) == f.get("sha"))


def net_bugs_line(gate, verdict, why, platform=None):
    """REG-3192 - the BUGS-ready line a safety-net find leaves (ASCII: it travels to Windows consoles). -> str"""
    return ("### REG-NNNN - THE SAFETY NET FOUND %s %s ON %s: a law trusted on another tree's proof over the same bytes "
            "(REG-3191) did not hold here. %s Reproduce: python3 tv/heart2.py --prove %s"
            % (gate, verdict, platform or sys.platform, str(why or "")[:200], gate))


@_under_census_lock
def _write_net(results, red=None, unmeasured=None):
    """REG-3192 - THE SAFETY NET'S VERDICTS. -> {"proved": [...], "finds": [...], "unjudged": [...]} | None (no census)

    A trusted gate judged PROVEN here leaves `trusted` (proved on this PC now) and any find or unjudged record on it. A
    clean run that went RED here (`red` - its first or its closing run), a BLIND or an INVALID is a FIND: recorded per
    gate in `netFinds` (its sha, verdict, the time it was first and last seen, how often, the platform, a BUGS-ready line)
    and nowhere else. ⚠ It never touches `blind`, `gateShas` or the fingerprint, so it never turns the census stale and
    never closes every lock: his 2026-09-12 ruling (BLIND is not STALE, a BLIND closes every lock) stands for every
    other BLIND; his 2026-11-05 ruling narrows it ONLY for what the safety net finds, which closes only the locks whose
    guard set holds that law (self_arming._net_heart, the #156 per-lock machinery). A gate the net could not judge here
    (an UNKNOWN or timed-out run, a lane that never measured it) is `netUnjudged`, with how many tries. A found or
    unjudged gate STAYS trusted - the census still holds it on another tree's word - and net_owed asks it again after
    NET_RETRY_S, so neither a flaky red nor a slow run is the last word."""
    if not os.path.exists(STATE):
        return None
    try:
        with io.open(STATE, encoding="utf-8") as fh:
            prior = json.load(fh)
    except Exception as _e:
        print("  ⚠ REG-3192 %s would not parse (%s) - the safety net writes nothing over it"
              % (os.path.basename(STATE), type(_e).__name__))
        return None
    gates = gate_files()
    shas = gate_shas([(n, f) for n, f in gates if n in (results or {})])
    rec = prior.get("gateShas") if isinstance(prior.get("gateShas"), dict) else {}
    tr = dict(prior.get("trusted") or {}) if isinstance(prior.get("trusted"), dict) else {}
    finds = dict(prior.get("netFinds") or {}) if isinstance(prior.get("netFinds"), dict) else {}
    unj = dict(prior.get("netUnjudged") or {}) if isinstance(prior.get("netUnjudged"), dict) else {}
    red, unm = set(red or ()), set(unmeasured or ())
    now = int(time.time() * 1000)
    said = {"proved": [], "finds": [], "unjudged": []}
    _once = _CENSUS.setdefault("netSaid", set())     # a slice banks its snapshot every minute: count each run ONCE
    for n, v in sorted((results or {}).items()):
        sha = shas.get(n)
        if not sha or rec.get(n) != sha:
            continue                     # the file moved since the census took it: the census owes it, the net says nothing
        if v == PROVEN:
            tr.pop(n, None)
            finds.pop(n, None)
            unj.pop(n, None)
            said["proved"].append(n)
            continue
        is_red = v == UNPROVABLE and n in red
        if n not in unm and (v in (BLIND, INVALID) or is_red):
            _vw = "RED" if is_red else v
            _why = ("its clean run is RED here, untampered" if is_red else
                    "a proof of it stayed green tampered here" if v == BLIND else "a proof of it is INVALID here")
            _was = finds.get(n) if isinstance(finds.get(n), dict) and finds[n].get("sha") == sha else {}
            finds[n] = {"verdict": _vw, "sha": sha, "at": now, "since": _was.get("since") or now,
                        "seen": int(_was.get("seen") or 0) + (0 if n in _once else 1), "platform": sys.platform, "why": _why,
                        "line": net_bugs_line(n, _vw, _why)}
            if is_red and (_CENSUS.get("redCases") or {}).get(n):
                finds[n]["cases"] = list(_CENSUS["redCases"][n])[:40]     # REG-3324 - only these cases' locks close
            unj.pop(n, None)
            said["finds"].append(n)
            _once.add(n)
            continue
        _was = unj.get(n) if isinstance(unj.get(n), dict) and unj[n].get("sha") == sha else {}
        unj[n] = {"verdict": v, "sha": sha, "at": now, "tries": int(_was.get("tries") or 0) + (0 if n in _once else 1)}
        said["unjudged"].append(n)
        _once.add(n)
    # REG-3324 - a red that did not repeat on its re-check: kept, named, dated - and it closes nothing
    flk = dict(prior.get("netFlakes") or {}) if isinstance(prior.get("netFlakes"), dict) else {}
    for n, cases in sorted((_CENSUS.get("flakes") or {}).items()):
        if n in (results or {}) and shas.get(n):
            _was = flk.get(n) if isinstance(flk.get(n), dict) else {}
            flk[n] = {"sha": shas.get(n), "at": now, "cases": list(cases)[:40], "platform": sys.platform,
                      "seen": int(_was.get("seen") or 0) + 1}
            finds.pop(n, None)
    out = dict(prior)
    out.update(trusted=tr, netFinds=finds, netUnjudged=unj, netFlakes=flk)
    _tmp = "%s.net.%d.tmp" % (STATE, os.getpid())
    try:
        with io.open(_tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
        os.replace(_tmp, STATE)
    except BaseException:
        try:
            os.unlink(_tmp)
        except OSError:
            pass
        raise
    return said


def _clean_went_red(runs):
    """REG-3192 - did a clean run of this gate go RED here, untampered - the first one its proofs shared, or the CLOSING
    one (REG-1669)? An UNKNOWN run (a deadline, a signal) is not red. -> bool"""
    return any(isinstance(r, dict) and (r.get("ok") is False or r.get("closingRed") is True)
               for r in (runs or {}).values())


def _prove_gate(sandbox, name, filename, proofs, say):
    """Every proof of ONE gate, serially, inside ONE sandbox. -> (verdict, [verdict per proof])

    ⚠ LIFTED OUT OF prove()'s INNER LOOP WHEN THE OUTER LOOP WAS SPLIT INTO LANES — it is not a
    second copy of that policy, it is the only one, and both the one-lane and the many-lane paths
    call this same function. A rule that exists twice is how this repo's defects start.
    [[copy-drift]]
    #42 — at push time (and only then) the gate goes to _prove_gate_push: the same per-proof rule, plus the order, the
    declared widths and the stop.
    """
    try:
        _reset_lane_records(sandbox, say)                # REG-2598 - the gate before this one's records never reach it
    except Exception as _re:
        say("     ⚠ REG-2598 the run records a gate before %s may have written could not be checked (%s) - its proofs "
            "may be keyed over them" % (name, type(_re).__name__))
    if _PUSH is not None:
        return _prove_gate_push(sandbox, name, filename, proofs, say, _PUSH)
    verdicts = []
    _CLEAN.runs = {}                                     # REG-1669 — this gate's proofs share one clean run
    _cc = _CENSUS.get("cache")                           # #186 - the self-prove census serves and banks (his ruling)
    _CLEAN.pending = [] if _cc is not None else None     # a census PROVEN waits for the closing clean run, as a push's does
    try:
        _v0 = len(_VANISHED)                             # REG-3416 - what vanished from THIS gate's sandbox while it ran
        verdicts = _prove_gate_proofs(sandbox, name, filename, proofs, say)
        verdicts = _closing_clean(name, verdicts, say)
        _gone = [v for v in _VANISHED[_v0:] if v[0] == filename]
        if _CENSUS.get("net") and _clean_went_red(getattr(_CLEAN, "runs", None)) and _net_red_holds(name, say,
                                                                                                    vanished=_gone):
            _CENSUS["red"].add(name)                     # REG-3192 - a clean run of it went RED here: the net's find
        if _cc is not None:
            try:
                _census_bank(_cc, name, verdicts, say)
            except Exception as _be:                     # the bank may cost a re-prove, never this gate's verdict
                say("     %-52s   ↳ #186: its proofs could not be banked (%s) - the verdicts stand"
                    % (name, type(_be).__name__))
    finally:
        _CLEAN.runs = None
        _CLEAN.pending = None
    # REG-1686 — every proof judged only elsewhere: nothing was proven HERE, so the gate is not PROVEN here
    if verdicts and all(v == ELSEWHERE for v in verdicts):
        return UNPROVABLE, verdicts
    return (BLIND if BLIND in verdicts
            else INVALID if INVALID in verdicts
            else UNPROVABLE if UNPROVABLE in verdicts
            else PROVEN), verdicts


# ══ #150 (REG-2942) - A KILLED PUSH KEEPS WHAT IT PROVED, AND ONLY WHAT A GREEN CLEAN RUN BRACKETS ══════════════════════
# A push gate held every PROVEN in _CLEAN.pending until its CLOSING clean run (REG-1988), and _on_fatal_signal exited
# without banking - so a kill (the hook's deadline, a Ctrl-C, a dead terminal) mid-gate lost every proof that gate had
# already proved: for a law like test_control, 27 proofs at ~4 min, the whole gate. Banking each PROVEN the moment it
# came back is NOT sound, and the key being "the bytes" does not make it so: the proofs share ONE clean run, and a proof
# can go red because earlier runs drifted the sandbox (state outside the key) rather than because of its tamper - which
# is exactly what the closing run exists to catch. So the bracket stays and moves earlier: once CHECKPOINT_EVERY PROVENs
# wait and another proof is about to run, the gate's shared clean run(s) are asked again HERE. Green - every waiting
# PROVEN sits between two green clean runs, as the closing run would have left it - is banked and FLUSHED to disk now.
# Red, unknown or raising banks nothing and asks no further checkpoint; the closing run still judges the gate as before.
# It costs at most one clean run per CHECKPOINT_EVERY proved proofs, and a kill now loses at most that many proofs'
# work. [[stale-reading]] [[regression-guard]] Law: test_a_killed_push_keeps_what_it_proved.
CHECKPOINT_EVERY = 4


def _checkpoint_bank(name, per, say, run):
    """#150 - ask the gate's shared clean run(s) again mid-gate; green banks and flushes every waiting PROVEN. -> bool:
    True when green (or nothing needed asking), False when a clean run was red, unknown or raised (bank nothing)."""
    pend = getattr(_CLEAN, "pending", None)
    if not pend:
        return True
    for r in [r for r in (getattr(_CLEAN, "runs", None) or {}).values() if r.get("reused")]:
        _t0 = time.time()
        try:
            ok, tail = r["again"]()
        except Exception as _ce:
            ok, tail = None, "it raised %s" % type(_ce).__name__
        with run._lock:
            run.ckpt["runs"] += 1
            run.ckpt["s"] += time.time() - _t0
        if not ok:
            say("     %-52s   ↳ #150: a CHECKPOINT clean run is %s (%s) - its %d waiting PROVEN(s) are not banked here; "
                "the closing run decides" % (name, "UNKNOWN" if ok is None else "RED", str(tail)[:60], len(pend)))
            with run._lock:
                run.ckpt["red"] += 1
            _checkpoint_revoke(name, say, run)
            return False
    keep, n = [], 0
    for _i, _key, _entry in pend:
        if _bankable(per.get(_i) if isinstance(per, dict) else per[_i]):
            if callable(_key):                       # REG-2640 - the v2 key, taken now that a clean run brackets it
                _key = _key()
            if _key is None:                         # REG-2944 - a listing law whose trace cannot key it banks nothing
                run.cache.count("moved")
                continue
            _s = float(((run.proofs.get((name, _i)) or {}).get("s")) or 0)
            # ⚠ MARKED: a checkpoint's bank, until this gate closes green. A later red clean run of the same gate takes
            # it back (_checkpoint_revoke); a gate that closes clears the mark; one that never closes (a kill) leaves it,
            # so the next push can count what the checkpoint saved.
            _entry = dict(_entry, ckpt=int(run.t0 * 1000), ckptS=round(_s, 1))
            run.cache.store(_key, _entry)
            run.cache.count("stores")
            _ck = getattr(_CLEAN, "ckpt_keys", None)
            if isinstance(_ck, list):
                _ck.append((_key, _entry))
            with run._lock:
                run.proofs.setdefault((name, _i), {})["b"] = True
                run.ckpt["banked"] += 1
                run.ckpt["bankedS"] += _s
            n += 1
        else:
            keep.append((_i, _key, _entry))
    _CLEAN.pending = keep
    run.cache.flush()
    say("     %-52s   ↳ #150: checkpoint clean run green - %d PROVEN(s) banked and written now, not at the gate's end"
        % (name, n))
    return True


def _checkpoint_revoke(name, say, run):
    """#150 - a LATER clean run of this gate went red: every PROVEN an earlier checkpoint of it banked is taken back, and
    the disk is written now, so no push - this one resumed or the next - reuses a proof whose gate drifted. -> how many"""
    _ck = getattr(_CLEAN, "ckpt_keys", None) or []
    n = 0
    for _key, _entry in _ck:
        if run.cache.unstore(_key, _proven_at(_entry)):
            n += 1
    if _ck:
        del _ck[:]
        run.cache.flush()
        with run._lock:
            run.ckpt["revoked"] += n
        say("     %-52s   ↳ #150: a later clean run of this gate went RED - %d proof(s) an earlier checkpoint banked are "
            "taken back" % (name, n))
    return n


def _checkpoint_close(name, run):
    """#150 - the gate closed green: what its checkpoints banked would have been banked now anyway, so the checkpoint mark
    is cleared (a resumed push counts as SAVED only what a gate that never closed had banked). -> how many"""
    _ck = getattr(_CLEAN, "ckpt_keys", None) or []
    for _key, _entry in _ck:
        run.cache.store(_key, dict((k, v) for k, v in _entry.items() if k not in ("ckpt", "ckptS")))
    n = len(_ck)
    del _ck[:]
    return n


#: REG-3324 - a unittest failure line's case: "FAIL: test_x (module.Class)" / "ERROR: test_x (module.Class.test_x)"
_FAIL_CASE_RX = re.compile(r"^(?:FAIL|ERROR): (test\w+) \(([\w.]+)\)", re.M)


def _red_cases(tail):
    """REG-3324 - the case names a red run's output names. -> sorted ["Class.test_x", ...] ([] when it names none)"""
    out = set()
    for meth, where in _FAIL_CASE_RX.findall(str(tail or "")):
        parts = [x for x in where.split(".") if x and x != meth]
        out.add("%s.%s" % (parts[-1] if parts else "?", meth))
    return sorted(out)


#: v3883 (#129 item 5) - A RED IS RE-CHECKED ON A QUIET PC. MEASURED 2026-11-06 23:38Z on his Mac: under my load, the safety
#: net judged test_control RED, its immediate re-check (REG-3324) ran under the same load and was RED again, and the find
#: shut all nine locks; 25 min later, quiet, the same law ran 2,274 OK. So before the re-check the net waits - bounded - for
#: the 1-minute load per core to fall under NET_QUIET_LOAD; a red that repeats on a PC that stayed loaded through the whole
#: wait is judged UNDER LOAD: not a find (the gate stays trusted, closes nothing and is asked again), while a red that repeats
#: on a quiet PC is the find it always was. Windows has no load average: UNKNOWN load waits for nothing and the find stands
#: (fail closed), exactly as before.
NET_QUIET_LOAD = 0.75
NET_QUIET_WAIT_S = 600.0
NET_QUIET_POLL_S = 15.0


def _load_per_core(_getload=None, _cpus=None):
    """v3883 - the 1-minute load average per core. -> float | None (no load average here, or unreadable: UNKNOWN)"""
    try:
        n = _cpus if _cpus is not None else (os.cpu_count() or 0)
        if not n or n <= 0:
            return None
        return float((_getload or os.getloadavg)()[0]) / float(n)
    except Exception:
        return None


def _wait_for_quiet(_load=None, _sleep=None, _now=None):
    """v3883 - wait, at most NET_QUIET_WAIT_S, for the load per core to fall to NET_QUIET_LOAD. -> the load when it ended
    (None: UNKNOWN - nothing to wait for)"""
    load, sleep, now = (_load or _load_per_core), (_sleep or time.sleep), (_now or time.time)
    t0, lv = now(), load()
    while lv is not None and lv > NET_QUIET_LOAD and now() - t0 < NET_QUIET_WAIT_S:
        sleep(NET_QUIET_POLL_S)
        lv = load()
    return lv


def _net_red_holds(name, say, vanished=None):
    """REG-3324 (#103 - his 11-07 "if the river proves itself already why does every proof ... need to continue proofing it
    over and over again for it to unlock"). MEASURED 11-06 23:38Z on his Mac: the safety net judged test_control RED once,
    under a load I had put on his machine, and ONE red of one 2,274-case law closed all nine locks; 25 minutes later the
    same law ran 2,274 OK. So, in the SAFETY NET only (never a proof's own verdict - there red is a finding and is never
    asked again, REG-2351): a red clean run is re-run ONCE before it becomes a find. Green the second time is a FLAKE -
    recorded with the cases it named (netFlakes), said, and it closes nothing; red again (or a re-run that cannot finish)
    stands as the find, carrying the cases that failed so the lock rule can narrow to them. -> True when the find stands"""
    runs = getattr(_CLEAN, "runs", None) or {}
    red = [r for r in runs.values() if isinstance(r, dict) and (r.get("ok") is False or r.get("closingRed") is True)]
    if not red:
        return False
    if vanished:
        # REG-3416 - FILES VANISHED FROM THIS GATE'S SANDBOX WHILE IT RAN (#144): the red is the sandbox's, not the law's.
        # MEASURED on his Mac 11-08 03:44: 1,328 files gone mid-run (macOS's $TMPDIR sweep), test_control's closing clean
        # run RED, re-checked in the same broken sandbox, filed as a find - every lock it guards shut for 6 h over a law
        # that ran 2,274 OK quietly minutes later. Not a find and not a flake: the net could not judge it here (it stays
        # trusted, closes nothing, and is asked again).
        _CENSUS.setdefault("vanishedRed", {})[name] = sorted(set(str(v[1]) for v in vanished))[:40]
        say("     %-52s   ↳ REG-3416: its clean run went RED after %d file(s) VANISHED from its sandbox (#144) - the "
            "sandbox's verdict, not this law's: never a find, judged again" % (name, len(set(v[1] for v in vanished))))
        return False
    r = red[0]
    cases = _red_cases(r.get("tail"))
    again = r.get("again")
    ok, tail2 = None, ""
    _lv = None
    if callable(again):
        _lv = _wait_for_quiet()                       # v3883 - the re-check runs on a quiet PC when one comes in time
        try:
            ok, tail2 = again()
        except Exception as _ae:
            ok, tail2 = None, "the re-check raised %s" % type(_ae).__name__
    if ok is True:
        _CENSUS.setdefault("flakes", {})[name] = cases
        say("     %-52s   ↳ REG-3324: its clean run went RED here once and its re-check came back GREEN - a FLAKE (%s): "
            "recorded, never a find, no lock closes" % (name, ", ".join(cases[:3]) or "the red run named no case"))
        return False
    if ok is not True and isinstance(_lv, (int, float)) and _lv > NET_QUIET_LOAD:
        # v3883 - the PC stayed loaded through the whole wait: the repeat says nothing the load did not
        _CENSUS.setdefault("loadedRed", {})[name] = round(float(_lv), 2)
        say("     %-52s   ↳ v3883: its red repeated, but this PC stayed loaded (%.2f per core, over %.2f) through %d s of "
            "waiting - judged UNDER LOAD: never a find, asked again" % (name, _lv, NET_QUIET_LOAD, int(NET_QUIET_WAIT_S)))
        return False
    _CENSUS.setdefault("redCases", {})[name] = sorted(set(cases) | set(_red_cases(tail2)))
    return True


def _closing_clean(name, verdicts, say):
    """REG-1669 — the gate's proofs shared one clean run; it must still be green after the last of them. -> verdicts

    A law whose state drifted across its proofs could otherwise go red for the drift and be credited with catching
    the tamper. Only when a clean run WAS shared; a red or unknown closing run keeps no PROVEN of this gate
    (UNPROVABLE, said).

    REG-1677 (the v3543 cross-family eye) — AND A REUSED CLEAN RUN MAY NOT BANK A BLIND OR AN INVALID EITHER. A proof
    judged on the cached green could miss its anchor (INVALID) or stay green tampered (BLIND) because an earlier proof's
    run left the sandbox changed - where its own fresh clean run would have gone red first (UNPROVABLE). BLIND and
    INVALID go on the census's blind list, and one BLIND shuts every lock on that PC. So the closing run is asked
    whenever a reused verdict could be banked (PROVEN, BLIND or INVALID), and a red, unknown or RAISING closing run
    makes PROVEN and every reused BLIND/INVALID UNPROVABLE; a first proof's BLIND, judged on its own fresh clean run,
    stands.

    REG-2351 (#42 R7) - A CLOSING RUN THAT COULD NOT FINISH IS ASKED ONCE MORE before the gate's proofs are thrown away.
    UNKNOWN (a deadline, a run a signal ended, a raise) said nothing about the sandbox, yet it took every PROVEN of the
    gate with it - test_control's 27 proofs are ~92 minutes of runs. A RED closing run is never asked again: red is a
    finding. A second UNKNOWN discards as before, and a retry that comes back green is a green clean run after the last
    proof, so the REG-1988 bracket holds."""
    runs = getattr(_CLEAN, "runs", None) or {}
    shared = [r for r in runs.values() if r.get("reused")]
    if not shared or not any(v in (PROVEN, BLIND, INVALID) for v in verdicts):
        return verdicts
    _reused = set()
    for r in shared:
        _reused.update(r.get("by") or ())
    for r in shared:
        for _ask in (1, 2):
            try:
                ok, tail = r["again"]()
            except Exception as _ce:                         # REG-1677 — a raise is UNKNOWN, never a BLIND gate
                ok, tail = None, "the closing clean run raised %s" % type(_ce).__name__
            if ok is not None or _ask == 2:              # REG-2351 - only a run that could not finish is asked again
                break
            say("     %-52s   ↳ REG-2351: the CLOSING clean run could not finish (%s) - asked once more before this "
                "gate's proofs are discarded" % (name, str(tail)[:80]))
        if ok is False:
            r["closingRed"] = True                       # REG-3192 - the safety net reads a RED closing run as a find
        if not ok:
            say("     %-52s %s - the CLOSING clean run is %s (%s): its proofs shared one clean run and the sandbox did "
                "not stay clean across them, so no PROVEN of this gate is kept, and no BLIND judged on the shared run"
                % (name, UNPROVABLE, "UNKNOWN" if ok is None else "RED", str(tail)[:60]))
            return [UNPROVABLE if (v == PROVEN or (j in _reused and v in (BLIND, INVALID))) else v
                    for j, v in enumerate(verdicts)]
    return verdicts


def _prove_gate_proofs(sandbox, name, filename, proofs, say):
    """Every proof of ONE gate, serially. -> [verdict per proof] (the loop _prove_gate has always run)"""
    verdicts = []
    for i, pr in enumerate(proofs):
        # ⚠⚠ ONE BAD PROOF MAY NOT TAKE THE WHOLE RUN WITH IT. This loop sits inside a
        # `try: ... finally:` with NO `except`, so an exception from _prove_one escaped
        # `prove()` entirely — and `_write_state(results)` is BELOW that try, so nothing
        # was ever banked. The census in control_app.py then read a file nothing had
        # refreshed and reported from it, indefinitely.
        # MEASURED 2026-09-17: a 4-tuple proof raised AttributeError on `pr.get("file")`,
        # 12 gates declared them, and the organ that exists to ask "can my own gates still
        # go red" died on the first one while still reporting a verdict.
        # The shape is fixed at the reader (_normalise_proofs); this is the SECOND lock,
        # because the next unreadable proof will be a shape nobody has thought of yet.
        # [[the-unjoined-end]] [[unknown-stays-unknown]]
        try:
            v = _census_one(sandbox, name, filename, pr, i, say)     # #186 - served, or run and banked
        except Exception as _pe:
            say("    proof %d raised %s — recorded BLIND, run continues: %s"
                % (i, type(_pe).__name__, str(_pe)[:120]))
            v = BLIND
        verdicts.append(v)
    return verdicts


def _prove_lane(lane, work, out, lock, sink, built, buffered=True, blank=None):
    """ONE lane: build a sandbox nobody else touches, then drain the shared queue into `out`.

    ⚠⚠ EVERY GATE THIS LANE TAKES COMES BACK WITH A ROW, INCLUDING WHEN THE LANE DIES HOLDING IT.
    A dropped row does not read as a failure, it reads as a shorter census — and v2882 already
    cost this file a "0 blind of 278" that was really 279 gates with one never asked about. A
    lane that RAISES marks the gate it was holding BLIND — the same policy _prove_gate applies to
    a single proof that raises, and BLIND exits non-zero. A lane that cannot build a sandbox takes
    no gate at all, so the healthy lanes still prove them.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """
    say = _LaneSay(sink, lock, buffered=buffered)
    holding = []
    root = None
    _LANE_LOCAL.n = lane          # #144 — _run_gate stamps this lane's ports into each gate
    try:
        sandbox, root = make_sandbox(say)
        built.append(bool(sandbox))
        if not sandbox:
            # ⚠ IT TAKES NOTHING. The first cut drained the whole queue into UNPROVABLE here, so
            # ONE lane that lost a race for disk would have STOLEN every gate from the healthy
            # lanes and reported the lot as "already red untampered" — a confident wrong sentence
            # about 500 laws, produced by the failure of one copy. A lane with no sandbox proves
            # nothing and says so; the others keep the work. If NO lane can build one, the queue
            # goes undrained and _prove_gates answers "nothing was proven", which is the same
            # answer the old single-sandbox loop gave. [[unknown-stays-unknown]]
            say("  ⚠ lane %d could not build a sandbox and therefore takes NO gate — the other "
                "lanes keep the work. UNKNOWN is not a verdict this lane may hand out." % lane)
            return
        say("  lane %d sandbox: %s" % (lane, sandbox))
        say.flush()
        while True:
            # #42 — a STOPPED push-time run takes no further gate; _prove_gates names what is left NOT RUN
            if _PUSH is not None and _PUSH.stop.is_set():
                break
            if _PUSH is not None and _PUSH.browser:
                _got = _PUSH.take(work)            # REG-1989 — a lane never parks behind the browser while work waits
                if _got is None:
                    break
                (name, filename, proofs), _slot = _got
            else:
                try:
                    name, filename, proofs = work.get_nowait()
                except Exception:
                    break
                _slot = _browser_slot(name)        # #42 — a browser gate waits for the one browser at push time
            holding = [(name, proofs)]
            try:
                with _slot:
                    v, per = _prove_gate(sandbox, name, filename, proofs, say)
            except Exception as _ge:
                say("    %s raised %s outside its own proofs — recorded BLIND, the run continues: "
                    "%s" % (name, type(_ge).__name__, str(_ge)[:120]))
                v, per = BLIND, [BLIND] * len(proofs)
                if blank is not None:
                    with lock:
                        blank.add(name)        # raised before any proof judged it: BLIND, and still owed
            with lock:
                out[name] = (v, per)
            holding = []
            # REG-1676 — a slice banks what it has proved AS IT GOES (see _slice_banker, set on _GATE_HOOK by prove()).
            # Never fatal: a bank that fails is said and the lane keeps proving - the slice's own write still runs.
            _hook = _GATE_HOOK.get("fn")
            if _hook is not None:
                try:
                    _hook(out, lock)
                except Exception as _be:
                    say("    ⚠ banking the slice so far raised %s - it is retried after the next gate"
                        % type(_be).__name__)
            say.flush()
    except Exception as _le:
        say("  ⚠ lane %d died: %s: %s" % (lane, type(_le).__name__, str(_le)[:140]))
        for _n, _p in holding:
            with lock:
                if _n not in out:
                    out[_n] = (BLIND, [BLIND] * len(_p))
                    if blank is not None:
                        blank.add(_n)          # the lane died holding it: BLIND, and still owed
    finally:
        _LANE_LOCAL.n = None
        say.flush()
        if root:
            _drop_sandbox(root)


#: REG-1676 — the per-gate hook the lanes call after recording a gate (prove() sets it for a SLICE, clears it after). A
#: module slot rather than a parameter so the lane and _prove_gates keep their shapes - one prover runs per process.
_GATE_HOOK = {"fn": None}
#: REG-1676 — how often (seconds) a slice may write its verdicts so far into the census; the gate scan costs ~1 s on his
#: Mac and a few on the ALT, so a bank per gate is throttled, and the slice's final write is never skipped
SLICE_BANK_EVERY_S = 60


def _slice_banker(blank, say=print, every_s=None, write=None):
    """REG-1676 — A SLICE BANKS WHAT IT HAS PROVED AS IT GOES. -> callable(out, lock)

    MEASURED on his ALT 2026-10-01: a 27-gate slice proved four once-BLIND gates PROVEN, then stood aside at "only 972 MB
    of memory left" before its end - and a slice wrote the census only at its end, so 70+ minutes of verdicts were
    thrown away, the BLIND records stood, and every lock on that PC (the river) stayed shut. Now each finished gate is
    banked through the same _write_state a slice ends with (a partial result merged over the census, atomically), at
    most once per `every_s`; a stand-aside then loses at most the gates since the last bank, and the lane reads the
    banked ones as progress, never a failure."""
    st = {"last": 0.0, "lk": threading.Lock()}
    every = SLICE_BANK_EVERY_S if every_s is None else every_s

    def bank(out, lock):
        if not st["lk"].acquire(False):
            return                                  # a bank is already writing: the next gate banks
        try:
            now = __import__("time").time()
            if now - st["last"] < every:
                return
            with lock:
                snap = {k: v for k, (v, _p) in out.items()}
                unm = set(blank or ())
            if snap:
                if write is not None:
                    write(snap, unm)                # REG-3192 - a safety-net run banks through its own writer
                else:
                    _write_state(snap, stamp=False, unmeasured=unm, measured=_reused_ages(_CENSUS.get("cache"), snap))
                st["last"] = now
        finally:
            st["lk"].release()
    return bank


def _net_bank(snap, unmeasured):
    """REG-3192 - a safety-net slice banks what it has judged so far, through _write_net only (never _write_state)."""
    _write_net(snap, red=_CENSUS.get("red"), unmeasured=unmeasured)


def _prove_gates(have, say=print, workers=None, blank=None):
    """Prove every gate in `have` across isolated lanes. -> ({name: verdict}, {name: [verdicts]})

    (None, None) means NOT ONE lane could build a sandbox — the same "nothing was proven" answer
    the old single-sandbox loop gave, so the caller still banks no state. A run where SOME lanes
    built a sandbox is not that: those gates were really judged, and the rest say UNPROVABLE.
    """
    # imported HERE and not at module scope on purpose: control_app.py imports heart2 on every
    # census read, and it never proves anything. [[copy-drift]]
    import queue as _queue
    from concurrent.futures import ThreadPoolExecutor
    if not have:
        return {}, {}
    n = prove_workers(len(have), say) if workers is None else max(1, int(workers))
    n = max(1, min(n, len(have)))
    work = _queue.Queue()
    for item in have:
        work.put(item)
    out, lock, built = {}, threading.Lock(), []
    blank = blank if blank is not None else set()      # filled under `lock` by the lanes, and by the sweep below
    say("  proving %d gate(s) in %d lane(s), one throwaway sandbox each" % (len(have), n))
    # ⚠ RESTORED IN A `finally`, because a module global left widened would silently extend every
    # later single-lane deadline in the same process — control_app.py imports this module and
    # keeps it. A dial that does not spring back is a dial nobody set. [[label-outlived-referent]]
    global DEADLINE_SCALE, LANES_NOW
    _prev_scale, _prev_lanes = DEADLINE_SCALE, LANES_NOW
    DEADLINE_SCALE = _deadline_scale(n, say=say)
    LANES_NOW = n
    try:
        if n == 1:
            _prove_lane(1, work, out, lock, say, built, buffered=False, blank=blank)
        else:
            say("  every gate's deadline is x%d while %d lanes are running, because the lanes "
                "make the load themselves" % (DEADLINE_SCALE, n))
            with ThreadPoolExecutor(max_workers=n) as ex:
                futs = [ex.submit(_prove_lane, i + 1, work, out, lock, say, built, True, blank)
                        for i in range(n)]
                for f in futs:
                    _e = f.exception()
                    if _e is not None:
                        # _prove_lane already catches Exception; reaching here means something got
                        # past its own handler, and the gates it was holding are covered by the
                        # missing-row sweep below. Never swallowed.
                        # [[feedback-silence-is-not-evidence]]
                        say("  ⚠ a lane raised past its own handler: %s" % type(_e).__name__)
    finally:
        DEADLINE_SCALE = _prev_scale
        LANES_NOW = _prev_lanes
    if built and not any(built):
        say("  no lane could build a sandbox — nothing was proven, and that is UNKNOWN, not clean.")
        return None, None
    # ⚠ NOBODY MAY VANISH. Every gate handed in comes back with a row even if the lane holding it
    # died before writing one — an absent row reads as "nothing to see". [[zero-needs-a-denominator]]
    missing = [(nm, prs) for nm, _fn, prs in have if nm not in out]
    if missing and _PUSH is not None and _PUSH.stop.is_set():
        # #42 — a STOPPED push-time run never reached these: NOT RUN, not BLIND - nothing was found wrong with them, and
        # the run is refused on the failure that stopped it, so nothing unrun is ever passed either
        say("  #42 the run stopped before %d gate(s) were reached — NOT RUN: %s"
            % (len(missing), ", ".join(nm for nm, _p in missing[:6])))
        for nm, prs in missing:
            out[nm] = (NOT_RUN, [None] * len(prs))
        missing = []
    if missing:
        say("  ⚠ %d gate(s) were never reached by any lane — recorded BLIND, never dropped: %s"
            % (len(missing), ", ".join(nm for nm, _p in missing[:6])))
        for nm, prs in missing:
            out[nm] = (BLIND, [BLIND] * len(prs))
            blank.add(nm)                      # never reached: nothing measured it, so the census still owes it
    return ({k: v for k, (v, _p) in out.items()},
            {k: p for k, (_v, p) in out.items()})


#: REG-2352 (#42 R11) — the names the last prove() was asked for that matched no gate; main() refuses on them
_PROVE_UNMATCHED = []
_INDEXED_NAME = re.compile(r"^(.+)\[(\d+)\]$")


def gate_named(want, name, filename):
    """REG-2352 (#42 R11) — does a --prove / --forecast name select the gate (name, filename)? -> bool (pure)

    THE ONE PREDICATE: prove(), _forecast_main() and unmatched_names() all ask it, so what a run proves and what it
    calls unmatched can never disagree. A gate is named by its registered name, by its file as gate_files() gives it, or
    by that file's basename. Round 3: a root-level gate's file is "../visual_lock_invariant.py" there, and
    unmatched_names took `visual_lock_invariant.py` as a match by basename while prove() matched by name or file only:
    `--prove visual_lock_invariant.py` proved nothing, named nothing, and exited 0."""
    w = str(want or "")
    return bool(w) and w in (str(name), str(filename), os.path.basename(str(filename)))


def gates_named(only, gates):
    """REG-2352 — the gates `only` selects by gate_named(). -> [(name, filename)]; every gate when `only` is empty"""
    return [(n, f) for n, f in (gates or []) if not only or any(gate_named(w, n, f) for w in only)]


def unmatched_names(only, gates):
    """REG-2352 (#42 R11) — the --prove names that select no gate (gate_named). -> [(name, why)] (pure)

    `--prove NAME[5]` matched nothing, printed "nothing to prove", and exited 0: a typo, or a proof index nobody can ask
    for, read as a proof that passed. A name with an index gets the hint it needs."""
    gates = list(gates or [])
    out = []
    for n in sorted(set(only or ())):
        if any(gate_named(n, gn, gf) for gn, gf in gates):  # UNMATCHED-BY-THE-ONE-PREDICATE
            continue
        m = _INDEXED_NAME.match(str(n))
        if m:
            out.append((n, "a proof index is not a gate name - `--prove %s` proves every proof of %s"
                        % (m.group(1), "that gate" if any(gate_named(m.group(1), gn, gf) for gn, gf in gates)
                           else "a gate of that name, and there is none")))
        else:
            out.append((n, "matches no gate this heart can prove (no registered python gate has that name or file)"))
    return out


def prove(only=None, say=print, detail=None, push=False, stopped=None, stamp=True, reuse=False, net=False):
    """Prove `only` (None: every declaring gate) and write the census. `reuse`: the self-prove lane's census (#186, and
    REG-3191's trust pass first). `net` (REG-3192): the SAFETY NET - these trusted gates proved on this PC, never on
    another tree's word, written only through _write_net, never into the census's verdicts. -> {gate: verdict}"""
    gates = gate_files()
    todo = gates_named(only, gates)                      # REG-2352 - the one predicate unmatched_names asks too
    # REG-2352 (#42 R11) — NO SILENT PROVE-NOTHING: every name that matches no gate is said here, and main() exits 2 on it
    _PROVE_UNMATCHED[:] = unmatched_names(only, gates) if only else []
    for _un, _uwhy in _PROVE_UNMATCHED:
        say("  ✗ REG-2352: %r %s - nothing was proven for it" % (_un, _uwhy))
    if push:
        _PUSH_RECORD["record"] = None                    # REG-2353 - a fresh record per push-time run
    with_proofs = [(n, f, red_proofs_in(f)) for n, f in todo]
    have = [(n, f, p) for n, f, p in with_proofs if p]
    # ⚠ v3476 — THE DENOMINATOR NAMES EVERY STATE. v3473 printed the warning but the count line
    # still filed an unreadable declaration under "do not", and read None (the file will not even
    # parse) as False — so an unparseable gate took the "declares nothing" path. Found by the eye on
    # v3473. None is UNKNOWN, and UNKNOWN gets its own column. [[unknown-stays-unknown]]
    _state = dict((n, red_proof_unreadable(f)) for n, f in todo)
    _unread = [n for n, _f in todo if _state.get(n) is True]
    _unparsed = [n for n, _f in todo if _state.get(n) is None]
    say("  %d gate(s) in scope · %d declare a red-proof · %d do not%s%s"
        % (len(todo), len(have), len(todo) - len(have) - len(_unread) - len(_unparsed),
           (" · %d UNREADABLE" % len(_unread)) if _unread else "",
           (" · %d will not PARSE" % len(_unparsed)) if _unparsed else ""))
    if _unread:
        say("  ⚠ %d DECLARE a RED_PROOF this prover CANNOT READ (ast.literal_eval refused it) — "
            "UNREADABLE, not absent, and none of it has run: %s" % (len(_unread), ", ".join(_unread[:6])))
    if _unparsed:
        say("  ⚠ %d gate file(s) will not PARSE, so whether they declare a proof is UNKNOWN: %s"
            % (len(_unparsed), ", ".join(_unparsed[:6])))
    if not have:
        say("  nothing to prove. That is the BACKLOG, not a clean bill of health.")
        if push:                                        # REG-2353 - a push that proved nothing is recorded all the same
            _PUSH_RECORD["record"] = {"v": 1, "at": int(time.time() * 1000), "proofs": 0, "seams": _heart2_seams(),
                                      "gates": sorted(n for n, _f in todo),
                                      "note": "nothing was proven - no gate in scope declares a red-proof"}
        return {}
    _ages = {}
    _blank = set()      # gates written BLIND that no proof measured - never banked as proved against their file
    _trusted = {}               # REG-3191 - what the census's trust pass wrote (never a push's)
    if push:
        # #42 — hooks/pre-push's run: declared widths, likeliest failure first, stop at the first, one browser at a time,
        # and (P3) a PROVEN reused only over byte-identical inputs - the cache is opened HERE and nowhere else
        _GATE_HOOK["fn"] = None         # #145 (the v3545 eye) - a push banks once at the end, never through a slice's banker
        _cache = open_cache(say)
        results, per_proof = _prove_push(have, say, stopped, cache=_cache, blank=_blank)
        _ages = dict(getattr(_cache, "measured", None) or {})     # gate -> oldest provedAt among its reused proofs
        if _SHARD.get("spec"):
            # REG-2585 - A SHARD IS NOT A CENSUS: it proved a slice of each gate it touched, so it writes no state; what it
            # leaves is its cache file and, once it has finished, the manifest an import checks
            if results is not None:
                _shard_finish(_cache, only, stopped, say)
            return dict((n, v) for n, v in (results or {}).items())
        if results is not None and not results:
            # ⚠ A STOP BEFORE ANY GATE WAS JUDGED TO THE END IS NOT AN EMPTY RUN. _write_state reads an empty result as a
            # FULL run that proved nothing and would wipe every standing proof (provedGates, blind) - so nothing is
            # written, and the stop itself refuses the push. [[unknown-stays-unknown]]
            say("  #42 no gate was judged to the end, so the census is left exactly as it was")
            return {}
    else:
        # REG-1676 — a SLICE (stamp=False) banks as it goes; a full run keeps its one write at the end
        _GATE_HOOK["fn"] = None if stamp else _slice_banker(_blank, say)
        if net:
            # REG-3192 - a SAFETY-NET run banks through _write_net only: its verdicts never reach `blind` or gateShas
            _GATE_HOOK["fn"] = _slice_banker(_blank, say, write=_net_bank)
        _CENSUS["cache"] = _census_cache(reuse, say)     # #186 - only the self-prove lane's census (--reuse) opens it
        _CENSUS["red"], _CENSUS["net"], _CENSUS["netSaid"] = set(), bool(net), set()
        _CENSUS["flakes"], _CENSUS["redCases"] = {}, {}     # REG-3324 - this pass's flakes and failing cases only
        if net:
            _CENSUS["here"] = set(n for n, _f, _p in have)          # REG-3192 - every proof judged on this PC
        elif _CENSUS["cache"] is not None:
            # REG-3191 - the census writes what the bank serves whole over these bytes BEFORE it proves anything, so a
            # lock waits only on the gates the bank cannot serve and on the environment self-check. Never on a push.
            try:
                _tp = trust_pass(_CENSUS["cache"], say=say, gates=gates) or {}
                _trusted = dict((n, PROVEN) for n in _tp.get("written") or [])
            except Exception as _te:
                say("  ⚠ REG-3191 the trust pass raised %s (%s) - nothing was written on the bank's word; this slice proves "
                    "as before" % (type(_te).__name__, str(_te)[:120]))
            have = [(n, f, p) for n, f, p in have if n not in _trusted]
            _CENSUS["here"] = set(n for n, _f, _p in have if env_gate(n, _p)[0])   # the environment self-check
        if not have:
            # every gate of this slice was written by the trust pass: an EMPTY result here would read as a full run that
            # proved nothing and wipe every standing proof (_write_state), so nothing more is written
            _CENSUS["cache"], _CENSUS["here"], _CENSUS["net"], _GATE_HOOK["fn"] = None, (), False, None
            return _trusted
        try:
            results, per_proof = _prove_gates(have, say, blank=_blank)
        finally:
            _GATE_HOOK["fn"] = None     # #145 (the v3545 eye) - a raise must not leave this slice's banker installed
            _ccache, _CENSUS["cache"] = _CENSUS["cache"], None
            _CENSUS["here"], _CENSUS["net"] = (), False
        if _ccache is not None:
            _ages = _reused_ages(_ccache, results or {})
            say("  " + _ccache.summary(sum(len(_p) for _n, _f, _p in have)).replace("#42 P3 CACHE", "#186 CENSUS CACHE", 1))
        if net:
            if results is None:
                return {}
            _said = _write_net(results, red=_CENSUS.get("red"), unmeasured=_blank) or {}
            say("  REG-3192 SAFETY NET: %d proved here (no longer trusted), %d FOUND (each closes only the locks its law "
                "guards): %s; %d could not be judged here"
                % (len(_said.get("proved") or []), len(_said.get("finds") or []),
                   ", ".join(_said.get("finds") or []) or "none", len(_said.get("unjudged") or [])))
            return results
    if results is None:
        return {}
    # `detail` is the per-PROOF verdict list, and it exists so an A/B can compare the lanes
    # against the serial loop proof by proof. "Both green" is not the same answer as "the same
    # answers": a faster prove that flips ONE verdict is a broken gate, not a speedup.
    if detail is not None:
        detail.update(per_proof)
    # REG-3191 - the trust pass wrote its gates already (with `trusted`); this run writes only the gates it proved, as a
    # partial write, so the census keeps both
    if stamp:
        _write_state(results, measured=_ages, unmeasured=_blank)
    else:
        _write_state(results, measured=_ages, stamp=False, unmeasured=_blank)  # #99 — the slice flag only with --slice
    return results


def _lock_catchers(name, f, index):
    """#103 item 3 (REG-3484) - the classes this PC's red memory saw CATCH each lock's sabotages in this gate.
    -> {lock: [class]} ({} = the memory was read and holds none) | None (it could not be read: UNKNOWN - the lock's part
    then holds the classes that guard it by their own text, and lock_parts records no extra catcher). Read through
    _red_peek (the one read that marks nothing used)."""
    out = {}
    try:
        import self_arming as _sa
        red = dict((s, lks) for s, lks in ((index or {}).get("red") or []))
        for idx, pr in enumerate(red_proofs_in(f) or []):
            lks = red.get(_sa.red_entry_digest(pr))
            if not lks:
                continue
            ids = _red_peek(_red_key(name, idx, pr)) or ()
            cl = set(str(i).split(".", 1)[0] for i in ids)
            for lk in lks:
                out.setdefault(lk, set()).update(cl)
    except Exception:
        return None
    return dict((k, sorted(v)) for k, v in out.items())


def lock_shas_for(name, f, sha):
    """#103 item 3 (REG-3484) - the per-lock part a BROAD gate is banked with (self_arming.lock_parts). -> dict | None

    {"v", "sha": the bytes it was computed for - the same digest gateShas banks, "locks": {lock: {"d", "c"}}}. None for a
    focused gate, a file that will not read or parse, and bytes other than `sha` (the file moved under the run): that gate
    keeps the whole-file rule. A census writer runs in heart2's own processes, never the console's heap (#172)."""
    try:
        import self_arming as _sa
        text = _read_text(f if os.path.isabs(f) else os.path.join(HERE, f))
        if text is None or _sa._sha16(text) != sha:
            return None
        if sum(1 for lk in _sa.LOCK_DOORS if _sa._guards_lock(text, lk, _sa.LOCK_DOORS[lk])) < _sa.NET_NARROW_MIN_LOCKS:
            return None
        index = _sa.lock_index(text)
        parts = _sa.lock_parts(index, _lock_catchers(name, f, index))
        if not parts:
            return None
        return {"v": _sa.LOCK_PART_VERSION, "sha": sha, "locks": parts}
    except Exception:
        return None


def _lock_shas_merge(prior, results, unmeasured, gs, shas, files):
    """#103 item 3 - the census's lockShas after this write: every gate judged now re-recorded (or dropped), every record
    whose bytes are not the banked ones (gateShas) dropped - never carried onto other bytes. -> dict"""
    ls = dict(prior.get("lockShas") or {}) if isinstance(prior.get("lockShas"), dict) else {}
    for n in (results or {}):
        ls.pop(n, None)
        if n in (unmeasured or ()) or not shas.get(n) or gs.get(n) != shas.get(n) or not files.get(n):
            continue
        rec = lock_shas_for(n, files[n], shas[n])
        if rec:
            ls[n] = rec
    return dict((k, v) for k, v in ls.items() if isinstance(v, dict) and v.get("sha") and gs.get(k) == v.get("sha"))


@_under_census_lock
def _write_state(results, measured=None, stamp=True, unmeasured=None, trusted=None):
    """⚠ THE JOIN. Without this the whole loop is plumbing with no tap: `--prove` would measure
    beautifully and `_heart2_census()` in control_app.py would read an absent file and report
    UNKNOWN for ever, so the heart could never carry what the proving loop learned. This repo's
    single most repeated defect is two halves each built right and never joined.
    [[the-unjoined-end]] [[plumbing-with-no-tap]]"""
    gates = gate_files()
    have = [n for n, f in gates if red_proofs_in(f)]
    blind = sorted(n for n, v in (results or {}).items() if v in (BLIND, INVALID))
    # ⚠⚠ AN UNREADABLE STATE FILE IS NOT AN EMPTY ONE, AND THE DIFFERENCE IS THE WHOLE CENSUS.
    # This used to swallow a parse failure into `prior = {}`, which the merge below then treats as
    # "nothing was ever proven" — silently erasing `provedGates` and the `blind` list and writing
    # the wipe back over the only copy. Caught by tv/swallow_census.py (RANK 1: a failed read
    # handed back as DATA), which is this repo's own unknown-stays-unknown law mechanised.
    # A file that will not parse is a REFUSAL to write: the accumulated record survives, and the
    # next run says why. Losing the ledger is far worse than not updating it.
    # [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]
    prior = {}
    if os.path.exists(STATE):
        try:
            with io.open(STATE, encoding="utf-8") as fh:
                prior = json.load(fh)
        except Exception as _e:
            print("  ⚠ %s exists but would not parse (%s) — REFUSING to write, because merging "
                  "from an empty prior would erase every standing proof. Fix or remove the file."
                  % (os.path.basename(STATE), type(_e).__name__))
            return
    # ⚠⚠ MERGE, NEVER CLOBBER — and say when the run was PARTIAL. Two ways this erased real
    # findings: `--prove NAME` produced a one-gate `results` and rewrote the global `blind` list
    # from it, so checking one fix deleted every blind instrument the last full run found; and
    # `--ratchet` wrote a two-key dict that dropped `blind` entirely, flipping a DARK heart back
    # to WATCHED. A supervision layer that forgets its own findings is worse than one that never
    # made them. Partial runs now keep the prior blind list and mark themselves.
    _partial = bool(results) and len(results) < len(have)
    out = dict(prior)
    if _partial:
        _keep = [b for b in (prior.get("blind") or []) if b not in (results or {})]
        blind = sorted(set(blind) | set(_keep))
    # ⚠⚠ v2829 — A BLIND NAME MUST LEAVE WHEN ITS PROOF DOES, and it did not. The merge above keeps
    # a prior blind entry that this run did not re-test, which is right for a partial run — but it
    # never asked whether the gate still DECLARES a proof at all. #52's own workflow deletes a
    # RED_PROOF block whose tampers came back BLIND, precisely because a proof that survives its
    # own defeat is counted as coverage. Those five gates then sat in `blind` forever, so the heart
    # reported DARK over instruments that no longer claim anything. Measured 2026-09-09: blind 5,
    # every one a block that had just been removed.
    # This is the same defect `provedGates` had and was fixed for, in the neighbouring key.
    # [[label-outlived-referent]] [[the-unjoined-end]]
    blind = sorted(set(blind) & set(have))
    # ⚠⚠ `proved` IS DERIVED FROM A NAMED SET, NOT COUNTED PER RUN — AND THE MERGE ABOVE DID NOT
    # COVER IT. The comment beside it says "MERGE, NEVER CLOBBER" and then `proved` was recomputed
    # from THIS run's results alone, so `--prove ONE_GATE` rewrote the total from 20 to 1.
    # Measured 2026-09-09: proving a single new gate dropped the census to `proved: 1` while 20
    # gates were standing proven, and #52 is worked in exactly that batch-by-batch way — so the
    # one number he watches would have walked backwards every time progress was made.
    # A set of NAMES is the right model: partial runs accumulate, a gate that goes BLIND leaves,
    # and a gate whose file is gone leaves too. A COUNT cannot express any of that.
    _known = {n for n, _f in gates}
    _proved = set(prior.get("provedGates") or []) if _partial else set()
    for _n, _v in (results or {}).items():
        if _v == PROVEN:
            _proved.add(_n)
        else:
            _proved.discard(_n)          # BLIND/INVALID/UNPROVABLE revokes a standing proof
    _proved &= _known                    # a gate that no longer exists is not proven
    _pixel_unk = []
    _pixel = pixel_gates(gates, _pixel_unk)   # v2858 — by imports, not by grep
    # ⚠⚠ v2847 — EVERY VERDICT CARRIES ITS OWN AGE, BECAUSE ONE `ranAt` FOR THE WHOLE FILE IS A
    # DATE ON THE FETCH AND NOT ON THE THING. The merge above deliberately keeps a prior blind
    # entry the current run did not re-test — correct, and until now indistinguishable from one
    # measured seconds ago. MEASURED 2026-09-09: the file said `blind: 4` and `partial: true`, I
    # reported four blind instruments, and a re-prove returned **three of them PROVEN**. Their
    # verdicts had been carried forward across partial runs since before the fixes that closed
    # them, and nothing in the record could say so.
    #
    # `verdictAt` stamps each gate the run actually tested, so a reader can subtract: a blind name
    # with a fresh stamp is a live defect, a blind name with an old one is a claim nobody has
    # rechecked. Kept entries simply keep their old stamp — which is the point.
    # [[stale-reading]] [[inherited-claim-is-not-evidence]] [[unknown-stays-unknown]]
    _now_ms = int(__import__("time").time() * 1000)
    _seen = dict(prior.get("verdictAt") or {})
    _unm = set(unmeasured or ())
    for _n in (results or {}):
        # REG-1623 (the #231 eye on b135b25a) - a gate NOBODY MEASURED was not tested now: it keeps its old stamp (or
        # none). A fresh stamp here is the "this run tested it" the comment above promises, and it was not.
        if _n in _unm:
            continue
        _seen[_n] = _now_ms
    # ⚠ #42 P3 — A GATE THAT STANDS ON REUSED PROOFS WAS NOT MEASURED NOW. `measured` (gate -> epoch ms) is the oldest
    # provedAt among the cached proofs a push-time run reused for that gate; stamping it `_now_ms` would make 40 gates
    # read "just now" on a retried push when their proofs ran an hour or a day earlier - the defect the comment beside
    # oldestProofMs in control_app.py records, re-introduced one level down (second eye on the first cut). The stamp
    # can never be later than now, and a gate this run did not judge takes no stamp from the map.
    # [[stale-reading]] [[inherited-claim-is-not-evidence]]
    for _n, _ms in (measured or {}).items():
        if _n in (results or {}) and isinstance(_ms, (int, float)) and not isinstance(_ms, bool):
            _seen[_n] = min(_now_ms, int(_ms))
    _seen = {k: v for k, v in _seen.items() if k in _known}   # a gate that is gone keeps no stamp
    # ⚠⚠ #99 — A SLICE MAY NOT SPEAK FOR THE GATES IT DID NOT RUN. Every run stamped the whole-tree fingerprint, which is
    # right at push time (the hook proves exactly the gates that changed) and for a full run, and would be a lie from a
    # slice: one slice of a PC's first census would open every lock with 400 gates never run there. So each gate keeps
    # the digest of the file it was proved against (`gateShas`), and a slice (stamp=False) stamps the fingerprint only
    # when no declaring gate is owed any more. Until then the census stays unstamped, may() stays closed, and
    # self_prove proves the rest a slice at a time - which is how a PC he plays on ever finishes. [[unknown-stays-unknown]]
    _shas = gate_shas(gates)
    _gs = dict(prior.get("gateShas") or {}) if isinstance(prior.get("gateShas"), dict) else {}
    for _n in (results or {}):
        # second eye on v3528 (reproduced by reading): BLIND is also what a gate NOBODY MEASURED is written as - the
        # missing-row sweep in _prove_gates, a lane that died holding it, a gate that raised outside its own proofs.
        # Banking its digest said "proved against this file" about a gate that never ran, so it stopped being owed, no
        # slice ever ran it again, and the census read current with it blind - every lock on that PC shut for good over
        # a sandbox that failed once. An unmeasured row stays OWED; a MEASURED blind (the tamper ran and the law stayed
        # green) is banked, or one gate blind on Windows would keep the census from ever finishing. [[unknown-stays-unknown]]
        if _n in _unm:
            _gs.pop(_n, None)
            continue
        _gs[_n] = _shas.get(_n)
    _gs = {k: v for k, v in _gs.items() if k in _known}
    # #103 item 3 (REG-3484) - each BROAD gate banked now records its per-lock part beside the digest it was proved against
    _ls = _lock_shas_merge(prior, results, _unm, _gs, _shas, dict(gates))
    # REG-3191 / REG-3192 - WHO STANDS ON ANOTHER TREE'S WORD, AND WHAT THE SAFETY NET FOUND. `trusted` (the trust pass's
    # names) records each such gate at the sha it was written for; any other verdict this run wrote for a gate judged it
    # here, so it leaves the list (and a find on it is settled by that verdict). A record whose gate file has moved is
    # moot - the gate is owed again and judged afresh - so it is dropped, never carried onto other bytes.
    _trq = set(trusted or ())
    _tr = dict(prior.get("trusted") or {}) if isinstance(prior.get("trusted"), dict) else {}
    _nf = dict(prior.get("netFinds") or {}) if isinstance(prior.get("netFinds"), dict) else {}
    _nu = dict(prior.get("netUnjudged") or {}) if isinstance(prior.get("netUnjudged"), dict) else {}
    for _n in (results or {}):
        if _n in _trq and _n not in _unm:
            _tr[_n] = _shas.get(_n)
        else:
            _tr.pop(_n, None)
            _nf.pop(_n, None)
            _nu.pop(_n, None)
    _tr = {k: v for k, v in _tr.items() if v and v == _shas.get(k) and _gs.get(k) == v}
    _nf = {k: v for k, v in _nf.items() if isinstance(v, dict) and v.get("sha") and v.get("sha") == _shas.get(k)}
    _nu = {k: v for k, v in _nu.items() if isinstance(v, dict) and v.get("sha") and v.get("sha") == _shas.get(k)}
    _owed = [n for n in have if not _shas.get(n) or _gs.get(n) != _shas.get(n)]
    # ⚠⚠ REG-1623 (the #231 eye on b135b25a) - A RUN THAT KNOWS IT LEFT A GATE UNMEASURED MAY NOT STAMP. `stamp` let a
    # full or push-time run stamp the tree fingerprint whatever was owed - right for gates it simply did not run (the
    # hook proves only what changed), wrong for a gate it TRIED and could not measure: census_state called that census
    # current, may() stayed shut on the blind name, and the prover - which starts only on a census that is not
    # current - never ran it again. Nor may the PRIOR stamp stand: it can equal the tree's and read current all the
    # same. So no stamp at all: the census reads stale, the owed gate is named, and a slice measures it.
    _unm_owed = [n for n in _owed if n in _unm]
    if _unm_owed:
        _fp_out = None
    else:
        _fp_out = gates_fingerprint(gates) if (stamp or not _owed) else prior.get("gatesFingerprint")
    # v3862 (item 4) - AN OPEN ENVIRONMENT RE-PROVE: what it still owes (by the verdict stamps this run just wrote) keeps
    # the census unstamped, whoever writes; with none left the new environment becomes this PC's.
    _env_rec = env_load()
    _env_left = env_owed({"verdictAt": _seen}, _env_rec, have) if isinstance(_env_rec, dict) else []
    if _env_left:
        _fp_out = None
        _owed = sorted(set(_owed) | set(_env_left))
    else:
        _env_done = env_finish(_env_rec, _env_left)
        if _env_done is not None:
            env_save(_env_done)
    # ⚠⚠ REG-2355 — WHAT IS LEFT TO JUDGE UNDER THE NEW RULE IS CARRIED BY NAME. A gate judged now leaves the list
    # whatever its new verdict, so a slice always shrinks it - a flag stamped "once all are judged" kept re-owing the
    # ones already judged, and a slice of only those landed none and was booked a failure. slice_owed() owes the list
    # and self_prove reads the census stale while it is not empty.
    _rule_left = sorted(b for b in blind_rule_owed(prior) if b not in (results or {}) and b in blind)
    out.update({
        "blindRule": BLIND_RULE,
        "blindRuleOwed": _rule_left,
        "gateShas": _gs,
        "lockShas": _ls,
        "trusted": _tr,
        "netFinds": _nf,
        "netUnjudged": _nu,
        "sliceOwed": len(_owed),
        "sliceOwedSample": _owed[:12],
        "unstampedWhy": ("%d gate(s) this run could not measure are owed: %s"
                         % (len(_unm_owed), ", ".join(_unm_owed[:6])) if _unm_owed else
                         ("this PC's environment changed: %d gate(s) are proved again under it" % len(_env_left)
                          if _env_left else None)),
        "stampedBy": (None if _unm_owed else ("run" if stamp else ("slice-complete" if not _owed else None))),
        "proved": len(_proved),
        "provedGates": sorted(_proved),
        # v2858 — THE SPLIT, because one number hid a 93/7 one. See pixel_gates().
        "pixelTotal": len(_pixel),
        "pixelProved": len(_proved & _pixel),
        "pixelUnclassified": sorted(_pixel_unk),   # v2860 — NOT silently counted as backend
        "gatesFingerprint": _fp_out,   # v2862 — content, not mtime; #99 — a slice stamps only a COMPLETE census
        "backendTotal": len(gates) - len(_pixel) - len(_pixel_unk),
        # ⚠⚠ v2862 — MINUS THE UNCLASSIFIED TOO, or these two disagree. A cross-family review
        # found it: a gate that is PROVED and is now unreadable leaves backendTotal (which
        # subtracts _pixel_unk) but stays in backendProved (which did not), so backendProved
        # could exceed backendTotal. Zero unclassified today, so it has never fired — a
        # latent inconsistency in the one number he reads is exactly the kind that ships.
        "backendProved": len(_proved - _pixel - set(_pixel_unk)),
        "surfaces": surface_verdict(),   # v2859 — the PIXEL side, from the render run itself
        "declared": len(have),
        "unproven": len(gates) - len(have),
        "total": len(gates),
        "blind": blind,
        "blindUnchecked": sorted(b for b in blind if b not in (results or {})),
        "partial": _partial,
        "verdictAt": _seen,
        "ranAt": _now_ms,
    })
    # #99 — tmp + os.replace. A stand-aside can end the prover at any moment and slices write often; a kill inside a
    # plain open(..., "w") left the census truncated, and a census that will not parse is one this file then refuses
    # to write over - every lock shut for good on that PC. [[open-for-write-truncates-first]]
    _tmp = "%s.%d.tmp" % (STATE, os.getpid())
    try:
        with io.open(_tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
        os.replace(_tmp, STATE)
    except BaseException:
        try:
            os.unlink(_tmp)
        except OSError:
            pass
        raise


def resolve_proof_target(base, rel):
    """Where a RED_PROOF's `file` actually lives. -> str

    tv/ first, then the repo root one level up — because 59 of 259 gates name `bible.html`, which
    sits at the root, and resolving it only against tv/ made 23% of the suite UNPROVABLE for want
    of a path (v2821).

    ⚠⚠ IT IS A FUNCTION BECAUSE THE SECOND COPY OF THIS RULE WENT STALE. v2821 fixed the resolution
    inside `_prove_one` and left `test_the_heart_can_see_its_own_instruments` joining against tv/
    only — so the engine could apply a proof that its own well-formedness law called malformed.
    MEASURED on CI: 8 red-proofs reported as "names a file that does not exist: 'bible.html'",
    every one of them applyable and correct. Two resolvers for one question, one of them fixed.
    [[copy-drift]] [[feedback-contradiction-is-the-finding]]
    """
    tgt = os.path.join(base, rel)
    if rel and not os.path.exists(tgt):
        alt = os.path.join(os.path.dirname(os.path.abspath(base)), rel)
        if os.path.exists(alt):
            return alt
    return tgt


def gate_spec(name):
    """The registered gate's argv tail, timeout and -c script. -> ([extra], timeout, script|None)

    ⚠⚠ v2887 — REG-856 WAS FIXED IN triage() AND NOT IN prove(), AND THE BUG ENTRY SAID SO.
    It recorded "prove() calls the same _run_gate" as a known consequence and then threaded the
    spec through only the new command. MEASURED two versions later, proving 47 gates:
        js-syntax             UNPROVABLE — clean run: timed out after 180s   (registered: 300s)
        corroborate-selftest  UNPROVABLE — ALREADY RED untampered            (registered: --selftest)
    Both are the dropped spec, not the gates. A fix applied to one of two call sites is a fix that
    has not been generalised, and naming the second site in prose is not the same as covering it.
    [[feedback-generalize-fixes]] [[the-unjoined-end]]
    """
    try:
        import run_gates as _rg
    except Exception:
        return [], 180, None
    for g in getattr(_rg, "GATES", []):
        if getattr(g, "name", None) == name:
            argv = list(getattr(g, "argv", []) or [])
            # ⚠⚠ v2888 — `-c` IS NOT A FILE, AND argv[2:] IS ITS SCRIPT BODY.
            # hover-wilson registers as [python, "-c", <2.4KB verdict script>, <abs path>]. The
            # blanket argv[2:] handed that whole script back as an ARGUMENT, so the proof ran
            # `python3 <sandbox>/hover_wilson.py "<script text>" "<REAL tree path>"` — i.e. the
            # module's own main() instead of the gate, pointed at UNTAMPERED source. It reported
            # BLIND, and BLIND was the honest verdict: nothing the tamper touched was ever
            # executed. Measured 2026-09-10: 1 of 281 gates uses -c, and 1 of 281 forwards an
            # absolute real-tree path — the same one. [[the-unjoined-end]] [[source-reading-guard]]
            if len(argv) > 2 and argv[1] == "-c":
                return [a for a in argv[3:] if isinstance(a, str)], getattr(g, "timeout", 180), argv[2]
            return [a for a in argv[2:] if isinstance(a, str)], getattr(g, "timeout", 180), None
    return [], 180, None


def _at_widths(widths):
    """#42 — ' at 1280x800' on a push-time proof's lines, '' on every other (so those lines read as they always did)"""
    if not widths:
        return ""
    import law_widths as _LW
    return " at %s" % _LW.label(widths)


@_quiet_stretch                         # REG-2631 - every law run and tamper write closes the keyer's quiet stretch
def _prove_one(sandbox, name, filename, pr, idx, say, widths=None, why=None, clean_only=False, dry=False):
    # REG-1686 — a proof that declared what this PC must have is judged only where it is (see ELSEWHERE above)
    _need = pr.get("needs") if isinstance(pr, dict) else None
    if _need:
        _lacks, _words = host_lacks(_need)
        if _lacks is None and _words.startswith("an undeclared capability"):
            say("     %-52s %s — it declares %s, which no probe knows" % ("%s[%d]" % (name, idx), INVALID, _words))
            return INVALID
        if _lacks:
            say("     %-52s %s — it needs %s, which this PC does not have; it is proven on a PC that does"
                % ("%s[%d]" % (name, idx), ELSEWHERE, _words))
            return ELSEWHERE
    # REG-2357 — a law whose every case skips off POSIX is judged only where POSIX is. A proof of it that declares no need
    # Windows lacks files BLIND there, so it is refused HERE, where it can be judged (see _OFF_POSIX_NEEDS)
    if str(_need or "") not in _OFF_POSIX_NEEDS:
        _po = _posix_only_of(sandbox, filename)
        if _po and _po[1] and _po[0] == _po[1]:  # POSIX-ONLY-LAW
            say("     %-52s %s — every one of its %d case(s) skips off POSIX, so on Windows its tamper is never judged "
                "and it files BLIND there (one BLIND shuts every lock on that PC): declare \"needs\": \"posix-signals\" "
                "(or \"posix\" / \"macos\") and it is judged where POSIX is" % ("%s[%d]" % (name, idx), INVALID,
                                                                              len(_po[1])))
            return INVALID
    # #42 — `widths` (a push-time proof's own declaration, from _prove_push_one) reaches BOTH runs below, so the clean
    # run and the tampered run measure the same viewports; None = every width, all this function ever did. `why`, when
    # a caller hands one in, learns whether an UNPROVABLE was a law ALREADY RED untampered (the push-time run stops on
    # that) or a run that could not judge at all (a deadline, a missing file - named, never failed).
    _w = {"widths": widths} if widths else {}
    tgt_rel = str(pr.get("file") or "")
    # ⚠⚠ v2821 — RESOLVE AGAINST tv/ FIRST, THEN THE REPO COPY'S ROOT.
    # `sandbox` is the copied tv/ directory, so a proof naming "bible.html" resolved to
    # <sandbox>/tv/bible.html and came back UNPROVABLE — while the file sits one level up at the
    # repo root. MEASURED: 59 of 259 gates read bible.html, so 23% of the suite could never prove
    # itself for want of a path.
    #
    # ⚠ THE CONTAINMENT CHECK IS WIDENED TO THE REPO COPY, NOT WEAKENED. It still refuses anything
    # resolving outside the throwaway copy — an absolute path, or ../.. climbing to the real tree.
    # tv/ is inside the repo copy, so every previously-legal target stays legal and nothing new is
    # reachable except files the copy itself contains.
    _repo_copy = os.path.dirname(os.path.abspath(sandbox))
    tgt = resolve_proof_target(sandbox, tgt_rel)
    # ⚠⚠⚠ THE SANDBOX WAS A CLAIM, NOT A FACT. os.path.join DISCARDS its prefix when the second
    # argument is absolute, and normalises `..` straight out of the tree:
    #     join(sandbox, "control_app.py")           -> <sandbox>/control_app.py
    #     join(sandbox, "/Users/.../control_app.py")-> /Users/.../control_app.py   ESCAPED
    #     join(sandbox, "../../BUGS.md")            -> /tmp/BUGS.md                ESCAPED
    # So one RED_PROOF written with an absolute path — a natural copy-paste out of an error
    # message — and this function TRUNCATES AND REWRITES a file in his real tree. The restore
    # lives in a `finally`; a SIGKILL or the 10-minute push ceiling (three recorded kills in this
    # repo) would leave the defect in place, and his console execs the working tree, so it would
    # be live on screen. The docstring said "the ORIGINAL tree must never be touched" and nothing
    # enforced it. Found by a cross-family review of the shipped bytes.
    # [[unknown-stays-unknown]] [[feedback-blind-fixture-green-gate]]
    try:
        _root = os.path.realpath(_repo_copy)
        _real = os.path.realpath(tgt)
        _contained = (os.path.commonpath([_root, _real]) == _root)
    except Exception:
        # ⚠ THE DEFAULT *IS* THE FAILURE HERE, DELIBERATELY — and swallow_census asks that such a
        # site say so in a comment rather than be silently exempt. If the path cannot be resolved
        # at all, the honest answer is "not proven to be inside the sandbox", and the only safe
        # action on that is to REFUSE this one tamper. Raising would abort the whole proving run
        # over a single unresolvable target. [[unknown-stays-unknown]]
        _contained = False
    if not _contained:
        say("     %-52s %s — %r resolves OUTSIDE the sandbox (%s). REFUSED: a proof may only "
            "tamper inside the copy." % ("%s[%d]" % (name, idx), INVALID, tgt_rel, _real))
        return INVALID
    find, repl = str(pr.get("find") or ""), str(pr.get("replace") or "")
    # ⚠⚠ v3241 — AN ABSENT COUNT IS NOT A DECLARED 1. `int(pr.get("matches") or 1)` reads a
    # missing key, a real 0 and a real 1 as the same number. That became live the moment
    # _normalise_proofs started handing through 4-tuple proofs, which carry NO count: 32 of them
    # would be silently measured against 1, and the first whose anchor appears twice would be
    # filed INVALID for a declaration nobody ever made.
    # The well-formedness law in test_the_heart_can_see_its_own_instruments already treats None
    # as "nobody declared one" and checks only `got >= 1`. Two readers, one field, two policies
    # is how this repo's defects start. Same rule both sides. Found by a cross-family review of
    # v3240, the version that introduced the None. [[unknown-stays-unknown]] [[copy-drift]]
    _declared = pr.get("matches")
    want = None if _declared is None else int(_declared)
    label = "%s[%d]" % (name, idx)

    if not tgt_rel or not os.path.exists(tgt):
        say("     %-52s %s — %s is not in the sandbox" % (label, UNPROVABLE, tgt_rel or "(no file)"))
        return UNPROVABLE

    # ⚠⚠ REG-1626 — A GATE WHOSE SUBJECT IS NOT ON THIS PC IS UNPROVABLE HERE, NEVER BLIND. The comment beside
    # proof_inputs() always said so ("absent: the sandbox never brought it, so the gate reads UNPROVABLE there") and
    # nothing did it: MEASURED on the ALT 2026-09-30, test_chronicle_template's PROOF_NEEDS (his hand-read footage,
    # which never leaves his Mac) was absent, all 12 laws skipped, the run exited 0, and the gate was filed BLIND -
    # which shuts every lock on that PC for good, over a law about data it will never hold. A PC can only prove what
    # it has; this one says it did not, and why, and asks no run to say otherwise. [[unknown-stays-unknown]]
    _needs = proof_needs_in(filename)
    # REG-1644 (the v3535 cross-family eye) - None is "its PROOF_NEEDS could not be read", never "it needs nothing":
    # make_sandbox and law_inputs both branch on it and this door did not, so a gate with an unreadable declaration went
    # to its clean run, and with its subject absent every law skipped, the run exited 0 and it was filed BLIND - the
    # lock-shut outcome REG-1626 ended for the readable shape. MEASURED 2026-10-01: 0 of 753 gate files hit it today.
    if _needs is None:
        say("     %-52s %s — its PROOF_NEEDS cannot be read, so whether its subject is on this PC is UNKNOWN: "
            "nothing is graded on a guess" % (label, UNPROVABLE))
        if why is not None:
            why["needsUnreadable"] = True
        return UNPROVABLE
    if _needs:
        _gone = [n for n in _needs if not os.path.exists(os.path.normpath(os.path.join(sandbox, n)))]
        if _gone:
            _here = os.path.exists(os.path.normpath(os.path.join(REPO, "tv", _gone[0])))
            say("     %-52s %s — its subject %s is %s (PROOF_NEEDS): nothing to grade here"
                % (label, UNPROVABLE, _gone[0], "not in the sandbox (it IS on this PC - the copy did not bring it)"
                   if _here else "not on this PC - it lives only where it was recorded"))
            if why is not None:
                why["absentSubject"] = _gone[0]
            return UNPROVABLE
    # REG-2353 (round 4) — the forecast asks every door above and stops HERE: before any run, and before the red memory
    # is asked (a recall marks a use). A proof decided above is never priced as a run (_decided_before_a_run).
    if dry:
        return None  # PROVE-ONE-DRY

    # 1. CLEAN RUN. A gate that is already red in the sandbox can prove nothing.
    _extra, _to, _script = gate_spec(name)
    # ⚠ THE DEADLINE IS THIS PROVER'S PATIENCE, NOT THE LAW. DEADLINE_SCALE is 1 on the
    # single-lane path, so that path is unchanged; with lanes running it widens by a measured
    # factor so a verdict can never be decided by how many copies of the prover are busy.
    _to = int(_to * DEADLINE_SCALE) if _to else _to
    # #42 lever 1 (REG-1710) — at push time, a plain unittest law whose sabotage was caught before is asked only of the
    # cases that caught it. PROVEN there is a proof; anything else falls through to the full proof below, unchanged.
    _rk = _red_key(name, idx, pr) if (_PUSH is not None and not _script and not _extra and not clean_only) else None
    _rids = _red_recall(_rk) if _rk else None
    _mark(once=True, f="narrow" if _rids else "full")   # REG-2353 - the path this proof is forecast to take, before a run
    if _rids and _prove_narrow(sandbox, label, tgt, tgt_rel, find, repl, want, filename, _to, _w, _rids, widths,
                               say) == PROVEN:
        _mark(a="narrow")                                # REG-2353 - and the path it took
        _say_posix_only_catch(sandbox, filename, label, _need, _rids, say)       # REG-2357 - its catching cases
        return PROVEN
    if _rids:
        _mark(fellThrough=True)                          # REG-2353 - the narrowed pair did not decide it; the full proof does
    _runs = getattr(_CLEAN, "runs", None)
    _ck = (filename, repr(_extra), repr(_script), _at_widths(widths), _to)
    _hit = _runs.get(_ck) if isinstance(_runs, dict) else None
    if _hit is None and isinstance(_runs, dict) and not clean_only and _PUSH is not None:
        # REG-1992 - the clean wave already ran this law untampered over the same bytes in another lane: reuse its GREEN
        # verdict, bound to THIS sandbox for the closing run (`reused` makes _closing_clean ask it here). A red never
        # reaches here - it stopped the run in the wave.
        _wv = (getattr(_PUSH, "clean_wave", None) or {}).get(_ck)
        if _wv is not None and _wv[0] is True:
            _hit = _runs[_ck] = {"ok": True, "tail": _wv[1], "reused": 0,
                                 "again": (lambda: _run_gate(sandbox, filename, timeout=_to, extra=_extra,
                                                             script=_script, **_w))}
    if _hit is not None:
        ok_clean, tail = _hit["ok"], _hit["tail"]           # REG-1669 — this gate's one clean run
        _hit["reused"] += 1
        _hit.setdefault("by", []).append(idx)                # REG-1677 — which proofs were judged on a reused clean run
    else:
        ok_clean, tail = _run_gate(sandbox, filename, timeout=_to, extra=_extra, script=_script, **_w)
        if isinstance(_runs, dict) and ok_clean is not None:
            _runs[_ck] = {"ok": ok_clean, "tail": tail, "reused": 0,
                          "again": (lambda: _run_gate(sandbox, filename, timeout=_to, extra=_extra,
                                                      script=_script, **_w))}
    if ok_clean is None:
        say("     %-52s %s — clean run%s: %s" % (label, UNPROVABLE, _at_widths(widths), tail))
        return UNPROVABLE
    if not ok_clean:
        _head, _sep, _red = str(tail).partition(" | red: ")
        say("     %-52s %s — it is ALREADY RED untampered in the sandbox%s (%s)"
            % (label, UNPROVABLE, _at_widths(widths), _head[:60]))
        if _sep:
            say("       ↳ its red case(s), named (REG-1877): %s" % _red[:700])
        if why is not None:
            why["red"] = True
        return UNPROVABLE
    if clean_only:
        return CLEAN                                     # REG-1992 - the wave asks the untampered run only

    with io.open(tgt, encoding="utf-8") as fh:
        original = fh.read()
    got = original.count(find) if find else 0
    # THE CARVED SCAR: a green sabotage is usually the sabotage's fault. Print the count.
    if got < 1:
        say("     %-52s %s — the tamper matched 0 time(s): its anchor is not in the file, so it "
            "changes nothing. The SABOTAGE is wrong, not the law." % (label, INVALID))
        return INVALID
    if want is not None and got != want:
        say("     %-52s %s — the tamper matched %d time(s), expected %d. The SABOTAGE is wrong, "
            "not the law." % (label, INVALID, got, want))
        return INVALID

    # 2. TAMPER
    # ⚠⚠ v3243 — AND THE THIRD READER OF THE SAME FIELD. v3241 made `want` None when nobody
    # declared a count, which is correct for the COMPARISON above — and this line passes it
    # straight to str.replace as the count, where `None` is a TypeError:
    #     "aa".replace("a", "b", None) -> 'NoneType' object cannot be interpreted as an integer
    # So every 4-tuple proof (32 of them, all count-less) would have raised here, at the exact
    # step that does the tampering — the fix for "the prover could not READ them" would have
    # become "the prover crashes while TAMPERING them". Caught by a cross-family review of v3241,
    # the version that introduced the None.
    #
    # One field, three readers: legal-with-no-count (_normalise_proofs), compare-only-if-declared
    # (here and the well-formedness law), and a literal argument to str.replace. Same rule
    # everywhere: nobody declared a number, so replace EVERY occurrence — which is exactly what
    # `got` counted and what the `got >= 1` check just accepted.
    # [[unknown-stays-unknown]] [[copy-drift]] [[the-unjoined-end]]
    _tampered = (original.replace(find, repl) if want is None
                 else original.replace(find, repl, want))
    # ⚠⚠ A NON-ZERO EXIT IS NOT PROOF THE LAW FIRED. `_run_gate` reduces the tampered run to
    # `returncode == 0`, so a SyntaxError or ImportError the tamper introduced would be credited
    # as "the law caught the defect" — the gate would be praised for a crash it never inspected.
    # A tamper that does not even parse cannot be evidence about anything. Checked for python
    # only; html has no cheap equivalent and is left as a known limit rather than a false claim.
    if tgt_rel.endswith(".py"):
        import ast as _ast
        try:
            _ast.parse(_tampered)
        except SyntaxError as _se:
            say("     %-52s %s — the tamper does not parse (%s). A gate reddened by a "
                "SyntaxError proves nothing about the law."
                % ("%s[%d]" % (name, idx), INVALID, str(_se)[:60]))
            return INVALID
    with io.open(tgt, "w", encoding="utf-8") as fh:
        fh.write(_tampered)
    _LAST_RED.pop(threading.get_ident(), None)
    _LAST_SKIPS.pop(threading.get_ident(), None)         # REG-2359 - only the tampered run's own skips are read below
    _mark(a="full")                                      # REG-2353 - the full tampered run is the path taken
    try:
        ok_tampered, tail2 = _run_gate(sandbox, filename, timeout=_to, extra=_extra, script=_script, **_w)
    finally:
        with io.open(tgt, "w", encoding="utf-8") as fh:
            fh.write(original)
    _caught = list(_LAST_RED.get(threading.get_ident()) or []) if ok_tampered is False else []  # REG-2357 - who caught it
    _skips = _LAST_SKIPS.pop(threading.get_ident(), None)                    # REG-2359 - why each of its cases skipped
    if ok_tampered is False and _rk:
        _red_remember(_rk, name, idx, _LAST_RED.pop(threading.get_ident(), None))   # #42 lever 1 — learn what caught it

    if ok_tampered is None:
        say("     %-52s %s — tampered run%s: %s" % (label, UNPROVABLE, _at_widths(widths), tail2))
        return UNPROVABLE
    if ok_tampered:
        # ⚠⚠ REG-2354 — EVERY CASE SKIPPED FOR WANT OF NODE, IN BOTH RUNS, ON A PC WITH NO NODE: THE TAMPER WAS NEVER JUDGED
        # HERE. The BLIND line below says exactly that ("ALL n law(s) SKIPPED - the tamper was never judged") and filed
        # BLIND anyway, and one BLIND shuts every lock on a PC. MEASURED on Dean's PC 2026-10-21 (no node on PATH): 53 of
        # its 56 BLIND were JS laws whose every case skipped in the clean run and the tampered one - 0 of 9 locks
        # permitted, 0 reels ever tombstoned. It is REG-1686's case without the declaration, so ALL of these must hold:
        # both runs skipped every case (the counts in their tails); this PC has no node on PATH; the gate's own source
        # reaches for node; and the skip watch saw each of the tampered run's skips, every one for what this PC lacks
        # (REG-2359 - the counts alone also excused a law that skipped for any other reason, his D2R install, his
        # footage, as long as its file mentioned node): node, by a reason that names it - at least one - or POSIX, by a
        # case the gate's source runs only on POSIX, on a PC that is not (Dean's PC is Windows too). Anything less is
        # judged as before - a PC with node, a skip the watch could not see, a skip for anything else - and a law that
        # should be excused anyway declares `"needs": "node"` on its proof (REG-1686). [[unknown-stays-unknown]]
        _want = None                                     # REG-2359 - what the skips were for, when every one was wanted
        if (not widths and _skipped_every_law(tail) and _skipped_every_law(tail2)
                and host_lacks("node")[0] is True and _gate_reaches_for_node(sandbox, filename)):
            _want = _skipped_for_want(tail2, _skips, (_posix_only_of(sandbox, filename) or (frozenset(),))[0],
                                      host_lacks("posix")[0] is True)  # REG-2359 - the skips are node's
        if _want:
            # REG-2359 (round 4) - only what was measured: BOTH runs' counts, and the TAMPERED run's reasons. The clean
            # run's reasons are not read - its verdict is often one run reused for the gate (REG-1669, REG-1992)
            say("     %-52s %s — both runs skipped every case (%s; %s); the skip watch read the tampered run's %d skip "
                "reason(s), each for what this PC lacks: %d name node (%r)%s, and this PC has no node on PATH. The "
                "tamper was never judged here; it is judged on a PC that has node"
                % (label, ELSEWHERE, _skip_count(tail, "clean"), _skip_count(tail2, "tampered"),
                   len(_want[0]) + len(_want[1]), len(_want[0]), str(_want[0][0][1])[:70],
                   (", %d case(s) run only on POSIX, which this PC is not" % len(_want[1])) if _want[1] else ""))
            return ELSEWHERE
        say("     %-52s %s ← %s" % (label, BLIND, blind_reason(pr.get("why"), got, tail2, widths=widths)))
        if widths:
            say("     %-52s   ↳ #42: GREEN at its DECLARED widths %s - the declaration is wrong (or the law is blind "
                "there); either way it proves nothing and the push refuses. Re-measure where the defect shows."
                % ("", _at_widths(widths).strip()))
        return BLIND
    say("     %-52s %s (%d match(es) tampered → red)%s" % (label, PROVEN, got, _at_widths(widths)))
    _say_posix_only_catch(sandbox, filename, label, _need, _caught, say)          # REG-2357 - its catching cases
    return PROVEN


# ── the census ───────────────────────────────────────────────────────────────────────────────
def report(say=print):
    gates = gate_files()
    have, missing = [], []
    for n, f in gates:
        (have if red_proofs_in(f) else missing).append((n, f))
    total = len(gates)
    say("♥ HEART 2.0 — can my own instruments still go red?")
    say("")
    say("    gates with a python file         %4d" % total)
    say("    declare an executable red-proof  %4d   (%.1f%%)"
        % (len(have), (100.0 * len(have) / total) if total else 0.0))
    say("    no proof — UNKNOWN, not clean    %4d" % len(missing))
    say("")
    if have:
        say("  proofs declared by:")
        for n, f in have:
            say("    · %s" % n)
    # ⚠⚠ v2853 — `len(have)` IS "DECLARES A PROOF", AND IT WAS RETURNED UNDER THE KEY `proved`.
    # Those are different questions and the whole of #52 is the gap between them: a gate can declare
    # a RED_PROOF that has never been executed, or one that came back BLIND, and this key called
    # both of them proven. MEASURED 2026-09-09: report() said proved=98 while 97 gates had actually
    # been tampered red — and `--ratchet` wrote that 98 into the census as the verified count.
    # The printed line above has always said "declare an executable red-proof". The KEY now agrees
    # with it. A verified count lives in `.heart2.json` under `provedGates`, written only by prove().
    # [[label-outlived-referent]] [[the-unjoined-end]]
    return {"total": total, "declared": len(have), "unproven": len(missing),
            "unprovenNames": [n for n, _ in missing]}


# ── the detector ─────────────────────────────────────────────────────────────────────────────
# Signatures of defects this repo has actually paid for. A detector that re-reports covered ground
# is noise, and noise is how a real finding gets scrolled past — so anything a gate already covers
# is DROPPED, not listed.
SIGNATURES = [
    ("fixed-size source window",
     re.compile(r"\[\s*\w+\s*:\s*\w+\s*\+\s*\d{2,}\s*\]"),
     "src[i:i+N] past the region reads as ABSENT — anchor both ends"),
    ("bare except that swallows a verdict",
     re.compile(r"except\s*:\s*\n\s*pass"),
     "a swallowed exception is UNKNOWN reported as fine"),
    ("open for write before the value exists",
     re.compile(r"open\(([^)]+),\s*[\"']w[\"']\)\.write\("),
     "open(p,'w').write(f()) empties p BEFORE f() runs"),
    # ⚠ BOTH FORMS, OR THE SIGNATURE ONLY SEES HALF THE REPO. Written first as `pkill\s+-f`,
    # which matches the shell string `pkill -f x` and MISSES `subprocess.run(["pkill", "-f", x])`
    # — and the argv list is how this repo actually spawns things. A signature that only knows one
    # spelling reports a clean file and means "I looked for the other one".
    ("cp -R of the repo or tv/",
     re.compile(r"""\bcp\b[^\n]{0,14}-R\b[^\n]{0,40}\b(tv|repo)\b"""),
     "tv/ holds 5.8 GB of footage; this caused an ENOSPC"),
    ("pkill by pattern",
     re.compile(r"""\bpkill\b[^\n]{0,14}-f\b"""),
     "cannot tell his process from mine — kill by port or PID"),
]


def _code_only(src):
    """Source with comments and DOCSTRINGS blanked out, everything else byte-for-byte. -> str

    ⚠⚠ THIS FUNCTION HAS BEEN WRONG TWICE, IN OPPOSITE DIRECTIONS, AND BOTH TIMES IT PRODUCED A
    CONFIDENT GREEN.

    First cut GREPPED RAW TEXT and returned ten hits, every one prose — it flagged safe_copy.py for
    "cp -R of the repo", a phrase that only appears in the docstring explaining why cp -R is
    forbidden, and it flagged THIS FILE twice for the comments warning against the very patterns it
    hunts. A detector whose findings are its own warnings is pure noise.

    Second cut over-corrected: it rebuilt the source by joining tokens with "\n" and dropped every
    STRING. That broke the detector in a way its own output could not show. MEASURED against a file
    containing a real `open(p, "w").write(g())`:

        raw text                    the open-for-write signature matches 1
        after the token rebuild     matches 0

    because the source became `open\n(\np\n,\n)\n.\nwrite\n(` — adjacency destroyed, and the
    `"w"` literal deleted outright. THREE of the five signatures were structurally dead:
    `open(...,'w').write(`, `pkill -f` and `cp -R ...` all live inside string literals or
    subprocess argument lists, which is precisely what it was deleting. So "no uncovered signature
    found — a measurement over 5 signature(s)" was a green produced by the instrument, not by the
    code: the exact failure this file exists to catch, inside the file that catches it.

    THE FIX IS TO BLANK, NOT TO REBUILD. Comment and docstring spans are overwritten with spaces
    (newlines kept), so every other byte stays where it was: adjacency holds, string literals
    survive, and prose still cannot match. [[source-reading-guard]] [[feedback-comments-vs-code]]
    """
    import tokenize
    import ast as _ast
    try:
        lines = src.splitlines(keepends=True)
        offsets, run = [], 0
        for ln in lines:
            offsets.append(run)
            run += len(ln)

        def _pos(row, col):
            return offsets[row - 1] + col if 0 < row <= len(offsets) else None

        spans = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                a, b = _pos(*tok.start), _pos(*tok.end)
                if a is not None and b is not None:
                    spans.append((a, b))
        # docstrings: a bare string expression at the head of a module, class or function
        tree = _ast.parse(src)
        for node in _ast.walk(tree):
            if not isinstance(node, (_ast.Module, _ast.ClassDef,
                                     _ast.FunctionDef, _ast.AsyncFunctionDef)):
                continue
            body = getattr(node, "body", None) or []
            if not body:
                continue
            first = body[0]
            if isinstance(first, _ast.Expr) and isinstance(first.value, _ast.Constant) \
               and isinstance(first.value.value, str):
                a = _pos(first.lineno, first.col_offset)
                b = _pos(first.end_lineno, first.end_col_offset)
                if a is not None and b is not None:
                    spans.append((a, b))
    except Exception:
        # ⚠⚠ None, NOT "". The comment below was right and the VALUE contradicted it. Caught by
        # tv/swallow_census.py (RANK 1: a failed read handed back as DATA) — this repo's own
        # unknown-stays-unknown law mechanised, catching it in the DETECTOR.
        # The caller does `src = _code_only(src)` and runs the signature regexes over the result.
        # An empty string yields ZERO hits, so a file that will not parse reads as a CLEAN file:
        # the exact defect this scanner exists to find, inside the scanner.
        # [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]
        return None
    out = list(src)
    for a, b in spans:
        for i in range(max(0, a), min(len(out), b)):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def detect(say=print):
    covered = set()
    for n, f in gate_files():
        covered.add(f)
    hits = []
    unscanned = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn in covered:
            continue
        p = os.path.join(HERE, fn)
        try:
            with io.open(p, encoding="utf-8") as fh:
                src = fh.read()
        except Exception:
            continue
        src = _code_only(src)
        if src is None:
            unscanned.append(fn)          # UNSCANNED is not CLEAN
            continue
        for label, rx, why in SIGNATURES:
            n_hits = len(rx.findall(src))
            if n_hits:
                hits.append((fn, label, n_hits, why))
    say("  scanned %d file(s) outside the gate set" % (len(os.listdir(HERE))))
    if unscanned:
        say("  ⚠ %d file(s) could not be parsed and were NOT scanned — UNKNOWN, not clean: %s"
            % (len(unscanned), ", ".join(sorted(unscanned)[:6])))
    if not hits:
        say("  no uncovered signature found. That is a measurement over %d signature(s), "
            "not a claim that nothing is wrong." % len(SIGNATURES))
    for fn, label, n_hits, why in hits:
        say("    %-34s %-30s x%-3d %s" % (fn, label, n_hits, why))
    return hits


# ── propose, never apply ─────────────────────────────────────────────────────────────────────
def propose(results, census, hits):
    """Write what a person should do. Never touch a guard. [[achilles-self-carving-system]]"""
    lines = ["# ♥ HEART 2.0 — proposals", "",
             "Written by `tv/heart2.py`. **It proposes; it never edits a guard.**", ""]
    blind = [n for n, v in (results or {}).items() if v == BLIND]
    invalid = [n for n, v in (results or {}).items() if v == INVALID]
    if blind:
        lines += ["## BLIND — survived its own defeat", ""]
        # ⚠ v2870 — AND IT MUST NOT CONTRADICT THE PROVE OUTPUT. Same review: after blind_reason
        # split "the law is weak" from "the laws never ran", stdout said one thing and this file
        # said the other about the same verdict — two writers, opposite jobs. It cannot re-run the
        # gate, so it names BOTH causes in the order the reader should check them, and points at
        # the line that already knows which. [[copy-drift]] [[the-unjoined-end]]
        # ⚠⚠ v2872 — THREE STATES, NOT TWO. v2870 stopped this contradicting the prove output and
        # then wrote an EXCLUSIVE sentence — "if it reports SKIPPED, the skip is the job,
        # OTHERWISE the law reads prose" — which is false for the case blind_reason exists to name:
        # five laws skipping while three RUN and stay green is BOTH jobs. The reader saw the word
        # SKIPPED and stopped at "fix the skip", which is the v2868 misdirection this was supposed
        # to close, left standing in the writer that cannot re-run the gate. [[copy-drift]]
        lines += ["- `%s` — the tamper reintroduced the defect and the gate stayed GREEN. Read the "
                  "`--prove` line for this gate; it reports one of three states. ALL laws skipped: "
                  "the tamper was never judged, fix the SKIP. SOME skipped: the laws that ran are "
                  "weak AND others opted out — both jobs. No skips: the law reads prose instead of "
                  "code, or asserts something the tamper does not touch." % n for n in blind] + [""]
    if invalid:
        lines += ["## INVALID PROOF — the sabotage, not the law", ""]
        lines += ["- `%s` — the tamper did not match the expected count. A sabotage that changes "
                  "nothing proves nothing." % n for n in invalid] + [""]
    if census.get("unproven"):
        lines += ["## UNPROVEN — the backlog (UNKNOWN, not clean)", "",
                  "%d gate(s) declare no executable red-proof. Each was proven red once, by hand, "
                  "and that proof survives only as prose." % census["unproven"], ""]
        # ⚠⚠ v2818 — A LIST OF NAMES IS A BACKLOG, NOT A PROPOSAL, AND THAT IS WHY 242 NEVER MOVED.
        # This wrote "these 242 gates declare no red-proof" and called it proposing. Every one of
        # them still required a person to re-derive by hand the sabotage the gate's OWN assertions
        # already state: a law that says assertIn("X", src_of_Y) IS the sabotage — remove X from Y
        # and it must go red. That derivation is mechanical, and leaving it manual is the whole
        # reason the number sat still while the engine around it worked.
        #
        # It still PROPOSES and never applies. What changed is that a proposal is now something a
        # person can paste, PRE-MEASURED: the anchor is counted in the real target file and only
        # an unambiguous one (exactly one occurrence) is offered. [[achilles-self-carving-system]]
        try:
            import heart2_candidates as _hc
        except Exception as _e:
            _hc = None
            lines += ["_(the candidate deriver could not be imported: %s)_" % type(_e).__name__, ""]
        _yield, _why_counts = 0, {}
        for n in census.get("unprovenNames", []):
            _f = None
            for _gn, _gf in gate_files():
                if _gn == n:
                    _f = _gf
                    break
            if _hc is None or not _f:
                lines.append("- `%s`" % n)
                continue
            _p, _status, _note = _hc.candidates_for(os.path.join(HERE, _f))
            _why_counts[_status] = _why_counts.get(_status, 0) + 1
            if _p:
                _yield += 1
                lines += ["", "### `%s`" % n, "", "```python", _hc.render_block(n, _p).strip(),
                          "```", ""]
            else:
                lines.append("- `%s` — no candidate: %s" % (n, _note))
        # ⚠ THE DENOMINATOR, ALWAYS. A proposals file that lists only what it managed to derive
        # would read as "this is the work", when the undeliverable remainder is also the work.
        lines += ["", "**%d of %d unproven gates yielded a pre-measured candidate.** The rest are "
                  "named above with the reason: %s" % (_yield, census.get("unproven"),
                  ", ".join("%s=%d" % kv for kv in sorted(_why_counts.items()))), ""]
    if hits:
        lines += ["## UNCOVERED SIGNATURES", ""]
        lines += ["- `%s` — %s x%d — %s" % (f, l, n, w) for f, l, n, w in hits] + [""]
    with io.open(PROPOSALS, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return PROPOSALS


def triage(say=print):
    """Split the gates that carry NO red-proof into 'writable' and 'not provable here'.

    ⚠⚠ THE CENSUS COUNTED TWO DIFFERENT THINGS AS ONE. `proved / total` leaves a remainder, and
    every gate in it was reported the same way: unproven. But that remainder holds two populations
    that mean opposite things —

      • a gate nobody has written a sabotage for yet   -> WRITABLE, the number is a to-do list
      • a gate that CANNOT go red in this sandbox      -> a ceiling, and no amount of work moves it

    MEASURED 2026-09-10: `test_tasks_ships_are_recorded` is green on his Mac and red the moment it
    runs in a sandbox, because `safe_copy` copies files and not `.git`, so the gate's own subject
    ("git named 0 shipped versions; 12 are needed") cannot exist there. Writing a red-proof for it
    would have produced UNPROVABLE — work spent to learn something the census could have told me.

    A gate with no proof is never RUN by --prove, so nothing ever discovers which population it is
    in. This runs each one untampered, once, and asks. That is a measurement, not a heuristic: the
    first attempt at this counted `git` mentions with a regex, which would have put a gate that
    merely says the word git in the wrong column. [[unknown-stays-unknown]]
    [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
    """
    files = gate_files()
    todo = [(n, f) for n, f in files if not red_proofs_in(f)]
    say("")
    say("  %d gate(s) carry no red-proof — running each untampered to see which COULD be proven"
        % len(todo))
    # ⚠ make_sandbox RETURNS (tv_dir, root) — the FIRST element is already the tv/ directory,
    # which is why prove() hands it straight to _run_gate. Joining "tv" onto it again produced
    # TypeError on a tuple. Mirrored from prove()'s own two lines rather than guessed a second time.
    sandbox, _root = make_sandbox(say)
    if not sandbox:
        say("  no sandbox — the split is UNKNOWN, not empty")
        return {"writable": [], "unprovable": [], "why": "no sandbox"}
    # ⚠⚠ RUN THE GATE THE WAY THE SUITE RUNS IT, OR THE VERDICT IS ABOUT A COMMAND NOBODY ISSUES.
    # The first cut called _run_gate(sandbox, filename), which builds [python3, <file>] — dropping
    # the gate's ARGV TAIL and ignoring its registered TIMEOUT. Measured: 3 of the 8 gates this
    # reported as "not provable" were my own instrument.
    #   corroborate-selftest  real argv ends in `--selftest`; without it the LIVE corroboration ran
    #                         and reported real disagreements. With it: exit 0, "🟢 every invariant
    #                         can both hold and refuse".
    #   js-syntax (300s), test_control (900s)  — given _run_gate's 180s default, both timed out and
    #                         a timeout was filed as a property of the gate rather than of the clock.
    # [[feedback-suspect-the-instrument]] [[zero-needs-a-denominator]]
    writable, unprovable = [], []
    for name, fn_ in todo:
        _tail, _to, _scr = gate_spec(name)    # ONE reader, shared with _prove_one
        ok, out = _run_gate(sandbox, fn_, timeout=_to, extra=_tail, script=_scr)
        (writable if ok else unprovable).append((name, (out or "").strip().splitlines()[-1][:70]
                                                 if out else ""))
    say("  WRITABLE      %3d — green in the sandbox, so a sabotage would mean something" % len(writable))
    say("  NOT PROVABLE  %3d — already red untampered; a red-proof here can only say UNPROVABLE"
        % len(unprovable))
    for n, why in unprovable[:12]:
        say("     %-46s %s" % (n[:46], why))
    if len(unprovable) > 12:
        say("     ... and %d more" % (len(unprovable) - 12))
    return {"writable": [n for n, _ in writable], "unprovable": [n for n, _ in unprovable]}


# ══ v3865 REG-3193 / REG-3194 — AN IMPORT KEYS ITS PROOFS ON THE PC'S SPARE CORES, AND SAYS HOW FAR IT IS ═════════════
# MEASURED 2026-11-05 on his Mac: `heart2 --import-shards` - the console's import of GitHub's proofs after an update
# (proof_release.import_bundle) - took 1,278 s for v3863 (2,625 proofs) and 1,635 s for v3864 on ONE core, and every
# lock stays shut until it ends. The time is the keyer select() asks once per servable entry: a profile of the first 300
# entries of the v3864 bundle put 28 of 76 s in law_inputs' closure walks and the rest in _key's hashing (stamp masks,
# literal counts, relpaths), once per PROOF. _key is a pure function of this checkout's bytes, its tracked/kept sets and
# the law's closure, so a pool of worker processes computes it before select() runs: each law's RED_PROOF list, its
# closure, the v1 key of every proof the import names and each v2 variant the target already records for that proof
# (cache._variants, the one reader of them). key_for then takes those answers (pre=) for exactly the calls it would have
# made and computes here whatever a worker did not answer - a key is never decided twice, only computed earlier.
# The pool: spawn, never fork (REG-1653); pythonw on Windows (no console window); cores - 2, at most IMPORT_WORKERS_MAX,
# and no more than free memory above child_guard's floor holds at IMPORT_WORKER_MB each (the ALT has 8 GB); free memory
# or the core count UNKNOWN -> one at a time, here. A pool that fails is SAID and what it left is keyed here. A worker
# asks git nothing and leaves when its parent does. Law: test_an_import_keys_on_spare_cores_exactly_as_one_core_would.
# MEASURED 2026-11-05 on his Mac, the real v3864 bundle (8,577 entries, 1,499 laws) keyed into a scratch store at one
# commit: one core 1,782.6 s; 3 workers (what this PC chose: 10 cores, 2,574 MB free) 728.5 s; 8 workers 419.8 s - and
# 0 of the 8,577 keys differed from one core's, at either count. [[heart-first]] [[unknown-stays-unknown]]
# v3885 (his 11-08: "Dean's PC is pinning all 12 cores with eight worker processes ... cap it to like 5-6") - MEASURED on
# Dean's PC right after the v3883 update: 8 import workers + the console held 100% of 12 cores, its /api/status took
# 8.7 s and /api/river did not answer in 75 s (the Mac's: 0.5 s). Six at most: a 12-core PC keeps half its cores for
# the game and the console (the measured 8-worker key above took 420 s against 3 workers' 729 s; 6 sits between).
IMPORT_WORKERS_MAX = 6
#: the most proofs of one law in one job: a law with hundreds of proofs (test_control) is shared across the workers,
#: never left to one of them while the others wait - MEASURED on the first full run, one law's job ran on alone
IMPORT_JOB_PROOFS = 12
#: REG-3193 - what one import worker may hold. MEASURED keying the v3864 bundle: a worker peaked at 262 MB (3 workers)
#: and 247 MB (8); 400 leaves room for another python and a bigger tree
IMPORT_WORKER_MB = 400
#: how often a worker asks whether its parent is still there
IMPORT_WORKER_WATCH_S = 2.0
_IMPORT_ASK = object()


def _import_floor_mb():
    """REG-3193 - the free memory an import leaves the PC: child_guard.RAM_FLOOR_MB, the floor under which no
    secondary worker starts (one figure for every such worker; 1024 when child_guard cannot be read)."""
    try:
        import child_guard as _cg
        return int(_cg.RAM_FLOOR_MB)
    except Exception:
        return 1024


def import_workers(cpus=_IMPORT_ASK, free_mb=_IMPORT_ASK, floor_mb=_IMPORT_ASK):
    """REG-3193 - how many worker processes an import may key on here. -> (n, why); n 1 keys here, one at a time.
    Asked of os.cpu_count() and self_prove.free_mb() (child_guard's one memory reader) unless given; None is UNKNOWN."""
    if cpus is _IMPORT_ASK:
        cpus = os.cpu_count()
    if free_mb is _IMPORT_ASK:
        try:
            import self_prove as _sp
            free_mb = _sp.free_mb()
        except Exception:
            free_mb = None
    floor = _import_floor_mb() if floor_mb is _IMPORT_ASK else int(floor_mb)
    if not isinstance(cpus, int) or isinstance(cpus, bool) or cpus < 1:
        return 1, "this PC's core count is UNKNOWN"
    if not isinstance(free_mb, (int, float)) or isinstance(free_mb, bool):
        return 1, "this PC's free memory is UNKNOWN"
    by_cpu = min(IMPORT_WORKERS_MAX, cpus - 2)
    by_mem = int((free_mb - floor) // IMPORT_WORKER_MB)
    if by_cpu < 2:
        return 1, "%d core(s): two are left to the PC" % cpus
    if by_mem < 2:
        return 1, "%d MB free: a worker needs %d MB over a %d MB floor" % (free_mb, IMPORT_WORKER_MB, floor)
    n = min(by_cpu, by_mem)
    return n, "%d core(s), %d MB free" % (cpus, free_mb)


def _pool_executable(platform, exe, isfile=os.path.isfile):
    """REG-3193 - the interpreter an import's workers run under. -> path | None (the default, sys.executable). Pure.
    On Windows a python.exe parent hands its workers the pythonw.exe beside it: pythonw owns no console, so a worker
    never opens a window on his screen."""
    exe = str(exe or "")
    if platform == "nt" and exe.lower().endswith("python.exe"):
        w = exe[:-len("python.exe")] + "pythonw.exe"
        if isfile(w):
            return w
    return None


def _import_pool_context():
    """REG-3193 - spawn (a fork of a process that has loaded Quartz can wedge - REG-1653), pythonw on Windows."""
    import multiprocessing as _mp
    ctx = _mp.get_context("spawn")
    w = _pool_executable(os.name, sys.executable)
    if w:
        ctx.set_executable(w)
    return ctx


_KW = {}     # REG-3193 - one import worker's own state, set by _key_worker_init (empty in every other process)


def _key_worker_init(tracked, kept, store):
    """REG-3193 - a worker's start: a cache with no store of its own (`store` names a file that does not exist, in the
    parent's scratch dir) and the PARENT's tracked/kept sets - so it keys on exactly the parent's sets and asks git
    nothing (on Windows a git child of a console-less worker opens a window on his screen - control_app v3407). A
    watch thread ends the worker when its parent is gone: a killed import never leaves workers behind."""
    _KW["cache"] = _VerdictCache(path=store, say=lambda *a, **k: None, tracked=tracked, kept=kept)
    _KW["intern"] = {}
    try:
        import multiprocessing as _mp
        parent = _mp.parent_process()
    except Exception:
        parent = None
    if parent is None:
        return

    def _watch():
        while True:
            time.sleep(IMPORT_WORKER_WATCH_S)
            try:
                gone = not parent.is_alive()
            except Exception:
                gone = True
            if gone:
                os._exit(0)
                return                                 # reached only where _exit is a law's stub
    threading.Thread(target=_watch, daemon=True, name="heart2-import-worker-watch").start()


def _key_job(job):
    """REG-3193 - in a worker: every answer key_for may ask _key for, for one law's named proofs.
    job (gate, filename, [idx], {ident: [(unread, listed)]} | None) -> (gate, proofs | None (nothing here: the parent
    derives it), closure | None, {idx: {(unread, listed): (key, rels, why)}}, {parse memo entries this job added})"""
    gate, fn, idxs, variants = job
    c, pool = _KW["cache"], _KW["intern"]
    before = set(c.parsed)
    try:
        proofs = red_proofs_in(fn) or []
    except Exception:
        return gate, None, None, {}, {}
    same, out = {}, {}

    def _keep(got):          # one tuple per distinct input list, one string per path: the answer crosses a pipe
        t = tuple(pool.setdefault(x, x) for x in (got[1] or ()))
        return got[0], same.setdefault(t, t), got[2]
    for i in idxs:
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(proofs):
            continue
        pr, got = proofs[i], {}
        try:
            got[((), None)] = _keep(c._key(HERE, gate, fn, pr, ()))
            for un, ls in (variants or {}).get(c.ident(gate, fn, pr), ()):
                got[(tuple(un), ls)] = _keep(c._key(HERE, gate, fn, pr, tuple(un), ls))
        except Exception:
            pass                                     # whatever is missing, the parent keys itself
        out[i] = got
    return gate, proofs, c.closures.get((HERE, fn)), out, dict((k, v) for k, v in c.parsed.items() if k not in before)


def _keyer_calls(shards):
    """REG-3194 - how many times select() asks the keyer: once per servable entry. -> {(gate, idx): entries}"""
    import proof_shard as _PS
    out = {}
    for _k, ent, _assigned in shards or ():
        for e in (ent or {}).values():
            if isinstance(e, dict) and _PS.servable(e):
                pk = (str(e.get("gate")), e.get("proof"))
                out[pk] = out.get(pk, 0) + 1
    return out


def _variant_map(cache):
    """REG-3193 - {gate: {ident: [(unread, listed)]}}: every v2 variant the target (and its seed) records, as
    cache._variants gives it - the workers key exactly the variants key_for would ask for."""
    by = {}
    for e in list(cache.entries.values()) + list(cache.seed.values()):
        if isinstance(e, dict) and e.get("ident") and e.get("gate"):
            by.setdefault(str(e["gate"]), set()).add(e["ident"])
    out = {}
    for g, ids in by.items():
        m = dict((i, v) for i, v in ((i, cache._variants(i)) for i in ids) if v)
        if m:
            out[g] = m
    return out


def _prewarm_keys(st, shards, workers=None, say=None, progress=None, pool=None):
    """REG-3193 - the pool's half of _shard_keyer: the laws this import's servable entries name, keyed in worker
    processes; their answers land in st["pre"] and st["proofs"], their closures and parses in the cache's memos.
    `pool` (n, initializer, initargs) -> an executor is a law's seam. -> {"workers", "laws", "answered", "seconds", "why"}"""
    say = say or (lambda *a, **k: None)
    calls = _keyer_calls(shards)
    by_gate = {}
    for (g, i) in calls:
        if g in st["files"] and isinstance(i, int) and not isinstance(i, bool):
            by_gate.setdefault(g, set()).add(i)
    n, why = (int(workers), "%d asked for" % int(workers)) if workers else import_workers()
    rep = {"workers": n if n >= 2 else 1, "laws": len(by_gate), "jobs": 0, "answered": 0, "seconds": None, "why": why}
    if n < 2 or len(by_gate) < 2:
        say("  import: keying %d law(s) here, one at a time (%s)" % (len(by_gate), why if n < 2 else "too few to share"))
        rep["workers"] = 1
        return rep
    import concurrent.futures as _cf
    cache, t0 = st["cache"], time.time()
    vmap = _variant_map(cache)
    jobs = []
    for g, ix in sorted(by_gate.items(), key=lambda kv: (-len(kv[1]), kv[0])):   # the law with most proofs first
        ix = sorted(ix)
        for a in range(0, len(ix), IMPORT_JOB_PROOFS):
            jobs.append((g, st["files"][g], ix[a:a + IMPORT_JOB_PROOFS], vmap.get(g)))
    rep["jobs"] = len(jobs)
    scratch = tempfile.mkdtemp(prefix="heart2-import-")
    failed, broke = 0, None
    try:
        args = (cache.tracked, cache.kept, os.path.join(scratch, ".heart2_cache.json"))
        ex = (pool(n, _key_worker_init, args) if pool is not None else
              _cf.ProcessPoolExecutor(max_workers=n, mp_context=_import_pool_context(),
                                      initializer=_key_worker_init, initargs=args))
        with ex:
            futs = [ex.submit(_key_job, j) for j in jobs]
            try:
                for f in _cf.as_completed(futs):
                    try:
                        gate, proofs, clo, out, parsed = f.result()
                    except Exception as e:
                        failed += 1
                        broke = broke or type(e).__name__
                        continue
                    if proofs is None:
                        failed += 1
                        continue
                    st["proofs"][gate] = proofs
                    with cache.lock:
                        if clo is not None:
                            cache.closures.setdefault((HERE, st["files"][gate]), clo)
                        for k, v in parsed.items():
                            cache.parsed.setdefault(k, v)
                    got = 0
                    for i, ans in out.items():
                        if ans:
                            st["pre"][(gate, i)] = ans
                            if ((), None) in ans:
                                got += calls.get((gate, i), 0)
                    rep["answered"] += 1
                    if progress is not None:
                        progress.add(got)
            except BaseException:
                for f in futs:          # what has not started is never started; the running jobs end on their own
                    f.cancel()
                raise
    except Exception as e:
        broke = broke or type(e).__name__
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    rep["seconds"] = round(time.time() - t0, 1)
    if broke or failed or rep["answered"] < len(jobs):
        say("  ⚠ REG-3193 import: the worker pool answered %d of %d job(s) (%s) - the rest are keyed here, one at a "
            "time" % (rep["answered"], len(jobs), broke or "%d job(s) failed" % failed))
    say("  import: %d law(s) in %d job(s) keyed in %d worker(s) in %.0f s (%s)" % (
        len(by_gate), rep["answered"], n, rep["seconds"], why))
    return rep


#: REG-3194 - the one name the import's progress file may have (proof_release.PROGRESS_NAME names it the same)
IMPORT_PROGRESS_NAME = "progress.json"


class _ImportProgress(object):
    """REG-3194 - how far an import's keying has got, in a small JSON file the console reads while the import runs:
    {"done", "of", "etaS", "at", "phase"}. done/of count select()'s keyer calls (one per servable entry). etaS is None
    until 1% is done, and again once all are (what remains - the store's write - has no measured rate): None is UNKNOWN,
    never 0. Written at most every EVERY_S, atomically; a write that fails is skipped - progress never stops an import.
    Only a file named IMPORT_PROGRESS_NAME OUTSIDE this checkout is ever written: heart2 never edits a file of the tree."""
    EVERY_S = 2.0
    #: v3882 (his 11-08: "the 5 min thing isnt correlated correctly and synced properly to the numbers ... also on the alt
    #: pcs"). MEASURED on Dean's PC 03:03: the file said etaS 380-425 while the count moved 2,997 -> 3,029 in 60 s (0.53 a
    #: second: ~43 min for the 1,367 left) - the ETA was the rate SINCE THE START (~3.7 a second: the first keys go fast,
    #: the rest slow, slower still beside his game), six times too short. The rate is the RECENT one, over WINDOW_S; the
    #: start's average only until MIN_SPAN_S of history exists; no progress in the window is UNKNOWN, never a small number.
    WINDOW_S = 180.0
    MIN_SPAN_S = 30.0

    def __init__(self, path, of, clock=None):
        self.path, self.of, self.done = path, max(0, int(of)), 0
        self.clock = clock or time.time
        self.t0, self.wrote = self.clock(), None
        self.samples = [(self.t0, 0)]
        self.write("keying", force=True)

    def eta_s(self):
        now = self.clock()
        el = now - self.t0
        if self.of <= 0 or self.done < max(1, self.of // 100) or self.done >= self.of or el <= 0:
            return None
        if el < self.MIN_SPAN_S:
            return max(1, int(round(el * (self.of - self.done) / float(self.done))))
        start = now - self.WINDOW_S
        older = [smp for smp in self.samples if smp[0] <= start]
        base = older[-1] if older else self.samples[0]       # the count as the window began (or the first one kept)
        span, moved = now - base[0], self.done - base[1]
        if span <= 0 or moved <= 0:
            return None                        # no progress in the window: UNKNOWN, never a small number
        return max(1, int(round((self.of - self.done) * span / float(moved))))

    def add(self, n=1):
        self.done += max(0, int(n))
        now = self.clock()
        self.samples.append((now, self.done))
        while len(self.samples) > 2 and now - self.samples[1][0] > self.WINDOW_S:
            self.samples.pop(0)                # keep ONE sample older than the window: the rate's base
        self.write("keying")

    def write(self, phase, force=False):
        now = self.clock()
        if not force and self.wrote is not None and now - self.wrote < self.EVERY_S:
            return False
        self.wrote = now
        body = {"done": self.done, "of": self.of, "etaS": self.eta_s() if phase == "keying" else None,
                "at": int(now * 1000), "phase": phase}
        if os.path.basename(self.path) != IMPORT_PROGRESS_NAME or _inside(REPO, self.path):
            return False                        # only the import's own scratch file, never a file of this checkout
        try:
            with io.open(self.path + ".tmp", "w", encoding="utf-8") as fh:
                json.dump(body, fh)
            os.replace(self.path + ".tmp", self.path)
            return True
        except Exception:
            return False


#: REG-3193 - target -> (shards, say, progress) an import asked to be keyed on the spare cores; _shard_keyer(target)
#: takes it when it is built (inside select's own argument list, so the call reads as it always has)
_PREWARM_ASKED = {}


@contextlib.contextmanager
def _keys_prewarmed(target, shards, say=None, progress=None):
    """REG-3193 - while the block runs, the keyer _shard_keyer(target) builds is prewarmed for `shards` first."""
    _PREWARM_ASKED[target] = (shards, say, progress)
    try:
        yield
    finally:
        _PREWARM_ASKED.pop(target, None)


def _shard_keyer(target):
    """REG-2586 - (gate, proof index) -> the verdict-cache key THIS checkout's tv/ gives that proof, or None. The key
    is computed exactly as a push computes it (_VerdictCache.key_for), over the checkout's own bytes.
    REG-3193 - keyer.prewarm(shards, say, workers, progress) computes those keys' parts in worker processes first
    (_prewarm_keys) - at once, when an import asked for it (_keys_prewarmed); REG-3194 - each call the pool did not
    answer adds one to `progress`."""
    st = {}

    def _init():
        if "files" not in st:
            st["files"] = dict(gate_files(say=lambda *a, **k: None))
            st["cache"] = _VerdictCache(path=target, say=lambda *a, **k: None)
            st["proofs"] = {}
            st["pre"] = {}
            st["progress"] = None

    def prewarm(shards, say=None, workers=None, progress=None, pool=None):
        _init()
        st["progress"] = progress
        return _prewarm_keys(st, shards, workers=workers, say=say, progress=progress, pool=pool)

    def _key(gate, idx):
        fn = st["files"].get(gate)
        if not fn or isinstance(idx, bool) or not isinstance(idx, int):
            return None
        if gate not in st["proofs"]:
            st["proofs"][gate] = red_proofs_in(fn) or []
        proofs = st["proofs"][gate]
        if not 0 <= idx < len(proofs):
            return None
        try:
            return st["cache"].key_for(HERE, gate, fn, proofs[idx], pre=st["pre"].get((gate, idx)))[0]
        except Exception:
            return None

    def keyer(gate, idx):
        if "files" not in st:
            _init()
        try:
            return _key(gate, idx)
        finally:
            if st["progress"] is not None and ((), None) not in (st["pre"].get((gate, idx)) or {}):
                st["progress"].add(1)
    keyer.prewarm = prewarm
    asked = _PREWARM_ASKED.pop(target, None)
    if asked is not None:
        prewarm(asked[0], say=asked[1], progress=asked[2])
    return keyer


#: REG-3352 - at most this many keyer calls in one import batch (a law never splits: a larger law is a batch of its own)
IMPORT_BATCH_PROOFS = 1500
#: REG-3415 (v3882, his 11-08: "proofs being proven properly on all machines ... rivers flowing finally?"). MEASURED on
#: the work ALT 11-08 (8 GB, i3, keying one at a time - "790 MB free: a worker needs 400 MB over a 1024 MB floor"): the
#: v3880 import ran 5,425 s, was killed at proof_release's 5,400 s bound and banked NOTHING; the next run's to-do GREW
#: (4,227 -> 4,350 keyer calls) and keyed at ~0.7 a second - its first fixed batch of 1,500 (the shut locks' guards,
#: test_control first) never reached its write, so every run re-keyed the same batch: a livelock, and frame.release's
#: guards were never banked. A batch is now sized by TIME: the first holds IMPORT_FIRST_BATCH calls, each later one what
#: the measured rate keys in IMPORT_BATCH_TARGET_S (never under IMPORT_BATCH_MIN, never over IMPORT_BATCH_PROOFS), so
#: a kill loses one batch's minutes, never the run.
IMPORT_FIRST_BATCH = 150
IMPORT_BATCH_TARGET_S = 300.0
IMPORT_BATCH_MIN = 20


def _import_clock():
    """REG-3415 - the clock an import batch is timed by (a law's seam). -> seconds"""
    return time.time()


def _next_batch_size(calls, seconds, cap=None):
    """REG-3415 - the next import batch's size, from the last one's measured rate. -> int. Pure.
    `calls` keyer calls took `seconds`; a rate that cannot be measured keeps the first batch's size."""
    cap = IMPORT_BATCH_PROOFS if cap is None else int(cap)
    try:
        rate = float(calls) / float(seconds)
    except (TypeError, ValueError, ZeroDivisionError):
        rate = None
    if rate is None or rate != rate or rate <= 0:
        return max(1, min(IMPORT_FIRST_BATCH, cap))
    return max(1, min(cap, max(IMPORT_BATCH_MIN, int(rate * IMPORT_BATCH_TARGET_S))))


def _import_first_batch(shards, rank=None, size=None):
    """REG-3415 - the next import batch (REG-3352's rule: ranked laws first, a law never split) and what is left after
    it. -> (batch | None when nothing is left, rest). Pure."""
    for b in _import_batches(shards, rank, size):
        gs = set(str(e.get("gate")) for _k, ent, _a in b for e in (ent or {}).values())
        if gs:
            rest = [(k, dict((key, e) for key, e in (ent or {}).items() if str(e.get("gate")) not in gs), a)
                    for k, ent, a in shards]
            return b, rest
    return None, shards


def _guards_done(batch, rest, rank):
    """REG-3415 - did this batch bank the last of the ranked (shut-lock guard) laws? -> bool. Pure. True only when it
    held a ranked law and none is left to key: the one moment an early trust pass can open a lock."""
    if not rank:
        return False
    held = set(str(e.get("gate")) for _k, ent, _a in (batch or ()) for e in (ent or {}).values())
    left = set(str(e.get("gate")) for _k, ent, _a in (rest or ()) for e in (ent or {}).values())
    return bool(held & set(rank)) and not (left & set(rank))


def _served_keys(target):
    """REG-3352 - the keys `target` already serves (peek() would answer them). -> set; empty when it will not read"""
    import proof_shard as _PS
    try:
        body, _why = _read_store(target, _entries_shape)
        ent = (body or {}).get("entries") or {}
        return set(k for k, e in ent.items() if isinstance(e, dict) and _PS.servable(e))
    except Exception:
        return set()


def _unserved(shards, served):
    """REG-3352 - the shards with only the servable entries `served` does not hold. -> (shards, kept n, {key: entry})

    A kept entry is not keyed here: its key is already served on this PC, and merge_into keeps a served key as it is, so
    banking it again changes nothing. It still counts as banked for its shard (unbanked() asks `take.get(key) is e`)."""
    import proof_shard as _PS
    left, kept = [], {}
    for k, ent, assigned in shards or ():
        mine = {}
        for key, e in (ent or {}).items():
            if key in served and isinstance(e, dict) and _PS.servable(e):
                kept[key] = e
            else:
                mine[key] = e                  # select() decides the rest - what is servable is ITS rule, asked once
        left.append((k, mine, assigned))
    return left, len(kept), kept


def _import_order(target=None):
    """REG-3352 / #103-C - {gate: rank} of the owed laws that keep a door lock shut (self_arming), imported first. {} for
    any store but this PC's own (CACHE): the lock rank speaks for THIS PC's census, never a fixture's - a known empty.
    None when the census could not be asked (UNKNOWN, never an empty rank - the swallow ratchet's rank 1). Either way the
    import then goes by name; only the meaning differs."""
    if target is None or os.path.abspath(target) != os.path.abspath(CACHE):
        return {}
    try:
        import self_arming as _sa
        r = _sa.owed_guard_rank()
        return dict(r.get("rank") or {}) if isinstance(r, dict) else None
    except Exception:
        return None                                       # could not ask: UNKNOWN, and _import_batches goes by name


def _import_batches(shards, rank=None, size=None):
    """REG-3352 - the import's entries cut into batches BY LAW: the ranked laws first (rank, then name), then the rest by
    name; at most `size` entries a batch, a law never split. Each batch keeps every shard's (k, entries, assigned) shape
    select() reads. -> [shards]. Pure."""
    size = IMPORT_BATCH_PROOFS if size is None else max(1, int(size))
    rank = rank or {}
    by = {}
    for _k, ent, _assigned in shards or ():
        for _key, e in (ent or {}).items():
            by[str(e.get("gate"))] = by.get(str(e.get("gate")), 0) + 1
    order = sorted(by, key=lambda g: (0, rank[g], g) if g in rank else (1, 0, g))
    groups, cur, n = [], set(), 0
    for g in order:
        if cur and n + by[g] > size:
            groups.append(cur)
            cur, n = set(), 0
        cur.add(g)
        n += by[g]
    if cur:
        groups.append(cur)
    return [[(k, dict((key, e) for key, e in (ent or {}).items() if str(e.get("gate")) in gs), assigned)
             for k, ent, assigned in shards] for gs in groups]


def _import_write(target, take, say, out):
    """REG-3352 - one import batch into `target` through the stores' one locked writer. -> (ok, why); adds the batch's
    banked and evicted counts to `out` once the write landed."""
    import proof_shard as _PS
    got = {}

    def merge(disk):
        ent, added = _PS.merge_into((disk or {}).get("entries"), take)
        got["added"], got["evicted"] = added, _cache_evict(ent, CACHE_MAX)
        body = dict((k, v) for k, v in (disk or {}).items() if k not in ("format", "entries"))
        body.update(format=2, entries=ent)
        return body
    w_ok, w_why = _StoreFile(target, say).commit(merge)
    if w_ok:
        out["added"] = out.get("added", 0) + got.get("added", 0)
        out["evicted"] = out.get("evicted", 0) + got.get("evicted", 0)
    return w_ok, w_why


#: #103 - how often an import asks whether the console that started it is still there
IMPORT_PARENT_EVERY_S = 10.0


def _watch_import_parent(ppid, every=None, alive=None, quit=None):
    """#103 - an import ends when the console that asked for it is gone.

    MEASURED 11-07 ~12:45 IST on the OLD ALT: three `heart2 --import-shards` at once. Two were orphans of consoles that
    had already exited (parent GONE): one started 11-06 02:59 and had run 32 h keying v3876's bundle, one from 03:43.
    The live console's own import was the third. 457 MB of 7.9 GB free, and its river route timed out at 60 s. Killing
    the two orphans freed 575 MB. proof_release runs the import with subprocess.run, so the console's timeout dies with
    the console. Nothing else bounded the child.

    So the bound moves INTO THE CHILD, like the console's own _orphan_exit_loop. It holds however the console dies, and
    only an import that was TOLD its parent watches. It is safe to stop between writes: each write is atomic, under an OS
    lock that is released when the process exits. A stop loses only what was not yet written, and REG-3352 keeps what
    was. The next console asks for its own import.
    -> the watching thread"""
    every = IMPORT_PARENT_EVERY_S if every is None else every
    alive = alive or _pid_alive
    quit = quit or (lambda: os._exit(3))

    def _loop():
        while True:
            time.sleep(every)
            try:
                gone = not alive(ppid)
            except Exception:
                gone = False                 # a probe that cannot answer keeps the import: never a guessed death
            if gone:
                try:
                    sys.stderr.write("#103 the console that asked for this import (pid %s) is gone - the import ends; "
                                     "what it wrote is kept\n" % ppid)
                    sys.stderr.flush()
                except Exception:
                    pass
                quit()
                return

    t = threading.Thread(target=_loop, daemon=True, name="heart2-import-parent")
    t.start()
    return t


def import_shards(paths, say=print, target=None, progress=None, trust=False):
    """REG-2586 — `heart2.py --import-shards FILE...`: the shards' banked PROVENs into this machine's verdict cache, ALL OR
    NOTHING (tv/proof_shard.py says every rule). -> exit code: 0 imported, 2 refused (nothing written)
    REG-3194 - `progress` (--import-progress FILE) names the file _ImportProgress keeps while the keys are computed.
    REG-3415 - `trust` (--trust): the trust pass also runs the moment the batch holding the last of the shut locks'
    guards is written, so a lock opens at its guards, not at the end of a run its bound may kill."""
    import proof_shard as _PS
    target = target or CACHE
    _prog = None
    ok_h, head = _git("rev-parse", "HEAD")
    head = head.strip() if ok_h else ""
    bodies = []
    for p in paths or []:
        body, why = _read_store(p, _entries_shape)
        bodies.append((os.path.basename(os.path.dirname(os.path.abspath(p))) + "/" + os.path.basename(p), body, why))
    ok, why, shards = _PS.check_shards(bodies, head)
    if ok:
        ok_d, dirty = _tracked_dirty()
        if not ok_d or dirty.strip():
            ok, why = False, "this checkout's tracked files differ from its HEAD (or git could not say), so its keys are not HEAD's"
    out, _resumed, _wrote = {"added": 0, "evicted": 0}, 0, 0
    if ok:
        # REG-3352 - THE WHOLE SET'S SHAPE FIRST, BEFORE ANY KEY: a stray entry or a proof index that names no proof still
        # refuses it all, and nothing is written
        ok, why, _shape, skipped = _PS.select(shards, keyer=None)
    if ok:
        _dropped = []                                  # REG-2596 - a key this tree never gives is left out, named
        # REG-3352 - THEN ONLY WHAT THIS PC DOES NOT SERVE YET IS KEYED, A BATCH AT A TIME, EACH WRITTEN BEFORE THE NEXT.
        # MEASURED on his ALT 11-07: the re-ask for v3876's completed win32 set keyed all ~9,000 proofs again - most of
        # them already in from the first, partial import - ran past proof_release's 5,400 s bound and kept NOTHING (all or
        # nothing). A key this PC already serves is kept as it is by merge_into anyway, so keying it again could only cost.
        _all, _skipped_all = shards, skipped
        _left, _resumed, took = _unserved(shards, _served_keys(target))
        if progress:                                   # REG-3194 - how far the keying is, for the console
            _prog = _ImportProgress(progress, sum(_keyer_calls(_left).values()))
        _rank = _import_order(target)                  # the shut locks' guards first (#103-C)
        _size = _next_batch_size(None, None)           # REG-3415 - the first batch is small; the rest, sized by time
        _rest = _left
        while True:
            shards, _rest = _import_first_batch(_rest, _rank, _size)
            if shards is None:
                break
            _t_b, _n_b = _import_clock(), sum(_keyer_calls(shards).values())
            with _keys_prewarmed(target, shards, say=say, progress=_prog):   # REG-3193 - on the spare cores first
                ok, why, take, skipped = _PS.select(shards, keyer=_shard_keyer(target), dropped=_dropped, here=TREE_ID)
            if not ok:
                break
            _size = _next_batch_size(_n_b, _import_clock() - _t_b)
            w_ok, w_why = _import_write(target, take, say, out)          # the stores' one locked writer, per batch
            if not w_ok:
                ok, why = False, "%s could not be written (%s)" % (os.path.basename(target), w_why)
                break
            took.update(take)
            _wrote += 1
            say("    REG-3415 batch %d written: %d keyer call(s) in %.0f s; the next holds up to %d"
                % (_wrote, _n_b, _import_clock() - _t_b, _size))
            if trust and _rank and _guards_done(shards, _rest, _rank):
                say("    REG-3415 the shut locks' guards are banked - the trust pass runs now, not at the end")
                trust_now(say=say, only=sorted(_rank))
        shards, take, skipped = _all, took, _skipped_all
        if _prog is not None:
            _prog.write("writing" if ok else "refused", force=True)
    if not ok:
        say("  ✗ REG-2586 IMPORT REFUSED: %s. %s" % (why, (
            "Nothing was written to %s." % os.path.basename(target)) if not _wrote else (
            "%d batch(es) were written before it (each keyed here first); the rest was not." % _wrote)))
        return 2
    _stops = dict((b["shard"]["k"], b["shard"].get("stopped")) for _l, b, _w in bodies
                  if isinstance(b, dict) and isinstance(b.get("shard"), dict) and b["shard"].get("stopped"))
    _halted = len(_stops)
    _owed = _PS.unbanked(shards, take)
    if _prog is not None:
        _prog.write("imported", force=True)
    say("  ✓ REG-2586 IMPORTED %d shard(s) of HEAD %s: %d PROVEN entr(ies) banked, %d already served here and kept, "
        "%d not servable and never banked (ELSEWHERE, BLIND, undated...)%s. Each keeps the tree it was proved in, so "
        "a push's clean wave still runs each such gate clean here once (#242).%s"
        % (len(shards), head[:12], out.get("added", 0), len(take) - out.get("added", 0), skipped,
           (", %d evicted over the cap" % out["evicted"]) if out.get("evicted") else "",
           (" ⚠ %d shard(s) STOPPED on a failure: what they banked is sound, what they never ran is not banked, "
            "and the failure itself is still owed a fix." % _halted) if _halted else ""))
    say("    REG-3352 %d entr(ies) this PC already served were not keyed again; the rest was keyed and written in %d "
        "batch(es), each before the next" % (_resumed, _wrote))
    if _dropped:
        _dg = {}
        for _s, _g, _i in _dropped:
            _dg.setdefault(_g, []).append(_i)
        say("    ⚠ REG-2596 %d PROVEN entr(ies) in %d law(s) DROPPED, never banked: this checkout's bytes give them another "
            "key, so they could never be served here (a push still proves them): %s" % (
                len(_dropped), len(_dg), "; ".join("%s %s" % (g, sorted(v, key=str)[:6]) for g, v in sorted(
                    _dg.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12])))
    for _k in sorted(_stops):
        _st = _stops[_k]
        _at = ("%s[%s] %s" % tuple(_st[:3])) if isinstance(_st, (list, tuple)) and len(_st) >= 3 else str(_st)[:80]
        say("    ⚠ shard %d/%d STOPPED at %s: %d of its %d assigned proof(s) NOT banked - never run, or not PROVEN "
            "there; a push here still owes them" % (_k, len(shards), _at, _owed.get(_k, (0, 0))[0], _owed.get(_k, (0, 0))[1]))
    return 0


def export_runtime(which=None, run=None):
    """REG-3045 (#186, D3) - the runtime this PC proves under, as an export records it and a carried import compares it
    (proof_shard.runtime_refusal). -> {"platform", "python": "3.12", "node": "22" | "none" (no node on PATH, measured) |
    None (node is there and its version could not be read: UNKNOWN, which refuses a carried import)}"""
    which = which or shutil.which
    run = run or subprocess.run
    out = {"platform": sys.platform, "python": "%d.%d" % tuple(sys.version_info[:2]), "node": None}
    node = which("node")
    if node is None:
        out["node"] = "none"
        return out
    try:
        p = run([node, "--version"], capture_output=True, text=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        m = re.match(r"\s*v?(\d+)\.", str(p.stdout or ""))
        if p.returncode == 0 and m:
            out["node"] = m.group(1)
    except Exception:
        pass
    return out


#: v3862 (item 4, his ruling 2026-11-05: "a full proof once per PC or when its environment changes") - THE ENVIRONMENT A
#: PC PROVES UNDER, AND WHAT IT OWES WHEN THAT CHANGES. The census owes a gate only when its own test file changes
#: (gateShas), and the proof cache keys on file bytes alone - so a PC that moved from python 3.9 to 3.12, or a Windows
#: feature update, or node arriving, kept serving every proof it earned under the old one, and nothing re-proved.
#: .heart2_env.json (beside the census, gitignored) holds the fingerprint this PC last FULLY proved under. Only the
#: console's own self-prove lane observes and adopts it (env_observe) - a push or an SSH job may run another python, and
#: two writers judging two pythons would re-prove for ever. A changed fingerprint opens a PENDING re-prove: every
#: declaring gate whose verdict is older than the change is owed (slice_owed), proved WITHOUT the cache (self_prove), the
#: census stays unstamped until none is left (_write_state), and then the new fingerprint is the PC's. Any part that
#: cannot be read is UNKNOWN and nothing is compared - a timed-out `node --version` is never an environment change.
ENV_NAME = ".heart2_env.json"
ENV_KEYS = ("platform", "os", "python", "node", "autocrlf")
_ENV_FP = {}
#: REG-3264 (the Grok CLI on REG-3162, #231 6681926045) - how long one reading of this PC's environment stands. It was
#: cached for the life of the process ("the environment does not change under a running process"), and it does: a
#: Windows console puts node on its own PATH at first boot (node_runtime step 5), and `git config core.autocrlf` can be
#: set beside a running console - neither reached env_observe until a relaunch, so the old proofs kept being served.
ENV_FP_TTL_S = 600
_ENV_HAVE = {"at": 0.0, "have": None}


def _os_build():
    """The OS release a proof could differ across: macOS major, the Windows build, Linux kernel major. -> str | None"""
    try:
        import platform as _pf
        if sys.platform == "darwin":
            v = _pf.mac_ver()[0]
            return v.split(".")[0] if v else None
        if os.name == "nt":
            return str(sys.getwindowsversion().build)
        return _pf.release().split(".")[0] or None
    except Exception:
        return None


def env_fingerprint(refresh=False, runtime=None, os_build=None, git=None, now=None):
    """-> (fingerprint | None, parts). None when any part is UNKNOWN: never compared, never adopted. One reading stands
    ENV_FP_TTL_S (REG-3264 - a process's environment does change: node placed on its PATH, autocrlf set beside it);
    `runtime`/`os_build`/`git`/`now` are a law's seams."""
    _now = time.time() if now is None else now
    if (_ENV_FP and not refresh and runtime is None and os_build is None and git is None
            and _now - float(_ENV_FP.get("at") or 0) < ENV_FP_TTL_S):
        return _ENV_FP["fp"], dict(_ENV_FP["parts"])
    try:
        rt = runtime if runtime is not None else export_runtime()
    except Exception:
        rt = {}
    parts = {"platform": rt.get("platform"), "python": rt.get("python"), "node": rt.get("node"),
             "os": (os_build() if os_build else _os_build())}
    ok, out = (git or _git)("config", "--get", "--default", "unset", "core.autocrlf")
    parts["autocrlf"] = (out.strip().lower() or None) if ok else None
    fp = None
    if all(parts.get(k) not in (None, "") for k in ENV_KEYS):
        fp = hashlib.sha256(json.dumps(parts, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    if runtime is None and os_build is None and git is None:
        _ENV_FP.update(fp=fp, parts=dict(parts), at=_now)
    return fp, parts


def _env_path():
    return os.path.join(os.path.dirname(os.path.abspath(STATE)), ENV_NAME)


def env_load(path=None):
    """-> the record ({} when absent) | None (it exists and will not parse: UNKNOWN - never written over, never read)."""
    p = path or _env_path()
    if not os.path.exists(p):
        return {}
    try:
        with io.open(p, encoding="utf-8") as fh:
            body = json.load(fh)
        return body if isinstance(body, dict) else None
    except Exception:
        return None


def env_save(rec, path=None):
    p = path or _env_path()
    if os.path.basename(p) != ENV_NAME:      # heart2's own record, beside its census, refused by name like CACHE
        return False
    tmp = "%s.%d.tmp" % (p, os.getpid())
    try:
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, sort_keys=True)
        os.replace(tmp, p)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def env_step(rec, cur, parts, now_ms):
    """What a NEW reading of the environment does to the record. -> the new record, or None (nothing to write). Pure.

    UNKNOWN (cur None) changes nothing. No fingerprint yet: this PC's environment is adopted as it is (rollout never
    owes a re-prove). The same: nothing. Back to the proved one while a re-prove was open: the re-prove is dropped (the
    proofs were earned under exactly this). A new one: a re-prove opens, `since` now; the one already open: nothing."""
    if not cur or rec is None:
        return None
    rec = dict(rec)
    if not rec.get("fingerprint"):
        return {"fingerprint": cur, "parts": dict(parts or {}), "adoptedAt": int(now_ms)}
    if rec["fingerprint"] == cur:
        if rec.get("pending"):
            # REG-3289 (#55) - a re-prove HE ASKED FOR on this very environment is not "back to the proved one": it stays
            if rec.get("askedBy") and rec.get("pending") == cur:
                return None
            for k in ("pending", "pendingParts", "since", "askedBy"):
                rec.pop(k, None)
            rec["droppedAt"] = int(now_ms)
            return rec
        return None
    if rec.get("pending") == cur:
        return None
    rec.update(pending=cur, pendingParts=dict(parts or {}), since=int(now_ms))
    return rec


def env_owed(state, rec, have):
    """The declaring gates a pending re-prove still owes: no verdict, or one older than the change. -> sorted [name].
    Pure. No re-prove open -> []."""
    if not isinstance(rec, dict) or not rec.get("pending") or not isinstance(rec.get("since"), int):
        return []
    seen = (state or {}).get("verdictAt") if isinstance(state, dict) else None
    seen = seen if isinstance(seen, dict) else {}
    since = rec["since"]
    return sorted(n for n in have if not (isinstance(seen.get(n), (int, float)) and seen.get(n) >= since))


def env_full_reprove(now_ms=None, path=None, by="his click"):
    """REG-3289 (#55, his 11-05 idea: an optional button that proves everything on THIS PC "as a extra precaution and extra
    safety measure") - open a pending re-prove on the environment this PC has NOW, exactly as a changed environment
    opens one (REG-3162): every declaring gate whose verdict is older than `since` is owed, the self-prove lane runs its
    slices WITHOUT --reuse at its own low priority, and the census stays unstamped until none is left. Shared proofs
    stay the speed path; this is the per-PC safety net. -> {"ok", "since", "why"}. Never raises.

    Refused, with the reason: an environment that cannot be read (UNKNOWN is never a fingerprint), a record that will not
    parse, or a re-prove already open (one at a time - the meter already counts it)."""
    try:
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        rec = env_load(path)
        if rec is None:
            return {"ok": False, "why": "%s will not parse - nothing was opened" % ENV_NAME}
        if rec.get("pending"):
            return {"ok": False, "since": rec.get("since"),
                    "why": "a re-prove is already open on this PC (since %s) - it is being proved now" % rec.get("since")}
        cur, parts = env_fingerprint()
        if not cur:
            return {"ok": False, "why": "a part of this PC's environment could not be read (%s) - nothing was opened" % (
                ", ".join(k for k in ENV_KEYS if not parts.get(k)) or "?")}
        new = dict(rec)
        if not new.get("fingerprint"):
            new.update(fingerprint=cur, parts=dict(parts or {}), adoptedAt=now)
        new.update(pending=cur, pendingParts=dict(parts or {}), since=now, askedBy=str(by or "his click")[:60])
        if not env_save(new, path):
            return {"ok": False, "why": "%s could not be written - nothing was opened" % ENV_NAME}
        return {"ok": True, "since": now, "why": "every law that declares a proof is owed again on this PC from now"}
    except Exception as e:
        return {"ok": False, "why": "opening the re-prove raised %s" % type(e).__name__}


def env_finish(rec, owed):
    """A pending re-prove with nothing left owed: the new fingerprint is this PC's. -> new record | None. Pure."""
    if not isinstance(rec, dict) or not rec.get("pending") or owed:
        return None
    out = {k: v for k, v in rec.items() if k not in ("pending", "pendingParts", "since", "askedBy")}
    out.update(fingerprint=rec["pending"], parts=dict(rec.get("pendingParts") or {}),
               provedFrom=rec.get("parts"), provedAt=int(time.time() * 1000))
    if rec.get("askedBy"):                     # REG-3289 - when he last had this PC prove everything, kept on the record
        out["fullProvedAt"] = out["provedAt"]
    return out


def env_observe(now_ms=None, path=None):
    """THE CONSOLE'S SELF-PROVE LANE ONLY: read this process's environment and record what it means. -> (record, why).
    Never raises."""
    try:
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        rec = env_load(path)
        if rec is None:
            return None, "%s will not parse - the environment is UNKNOWN and the file is left as it is" % ENV_NAME
        cur, parts = env_fingerprint()
        if not cur:
            return rec, "a part of this PC's environment could not be read (%s) - nothing compared" % (
                ", ".join(k for k in ENV_KEYS if not parts.get(k)) or "?")
        new = env_step(rec, cur, parts, now)
        if new is not None:
            env_save(new, path)
            rec = new
        return rec, "pending" if rec.get("pending") else "steady"
    except Exception as e:
        return None, "the environment check raised %s" % type(e).__name__


def env_reprove_state(state=None, gates=None, path=None):
    """-> {"owed": [name], "from": parts, "to": parts, "since"} while a re-prove is open; {"owed": None, "unknown": why}
    when whether one is open cannot be told; else None. Never raises.

    v3866 (the #231 eye on v3862) - "could not tell" was None, the same answer as "none open", so a corrupt record or a
    failure after a pending one was found let self_arming arm a surface over a census it had just called stale. Callers
    that read only `owed` see nothing new; the lock reads `unknown` and fails CLOSED. [[unknown-stays-unknown]]"""
    try:
        rec = env_load(path)
        if rec is None:
            return {"owed": None, "unknown": "this PC's environment record exists and will not parse"}
        if not isinstance(rec, dict) or not rec.get("pending"):
            return None
        if state is None:
            with io.open(STATE, encoding="utf-8") as fh:
                state = json.load(fh)
        if gates is None and _ENV_HAVE.get("have") is not None and time.time() - _ENV_HAVE["at"] < 30:
            have = _ENV_HAVE["have"]          # a lock's may() asks on hot paths; the declaring set moves only with code
        else:
            have = [n for n, f in (gates if gates is not None else gate_files(say=lambda *a, **k: None))
                    if red_proofs_in(f)]
            if gates is None:
                _ENV_HAVE.update(at=time.time(), have=have)
        return {"owed": env_owed(state, rec, have), "from": rec.get("parts"), "to": rec.get("pendingParts"),
                "since": rec.get("since"), "asked": rec.get("askedBy")}
    except Exception as e:
        return {"owed": None, "unknown": "the open environment re-prove could not be read (%s)" % type(e).__name__}


def env_change_words(er):
    """'python 3.9 -> 3.12, node none -> 22' - the parts that moved. Pure."""
    a, b = (er or {}).get("from") or {}, (er or {}).get("to") or {}
    moved = ["%s %s -> %s" % (k, a.get(k), b.get(k)) for k in ENV_KEYS if a.get(k) != b.get(k)]
    if not moved and (er or {}).get("asked"):             # REG-3289 - nothing moved: he asked this PC to prove it all
        return "a full re-prove asked by %s" % er["asked"]
    return ", ".join(moved) or "an unrecorded part"


def _shard_decls():
    """REG-3044 - (gate, proof index) -> THIS checkout's declaration of that proof (its RED_PROOF dict), or None. The carry
    rule reads a proof's `needs` here, never from the file that carried it."""
    st = {}

    def decl(gate, idx):
        if "files" not in st:
            st["files"] = dict(gate_files(say=lambda *a, **k: None))
            st["proofs"] = {}
        fn = st["files"].get(gate)
        if not fn or isinstance(idx, bool) or not isinstance(idx, int):
            return None
        if gate not in st["proofs"]:
            st["proofs"][gate] = red_proofs_in(fn) or []
        proofs = st["proofs"][gate]
        return proofs[idx] if 0 <= idx < len(proofs) and isinstance(proofs[idx], dict) else None
    return decl


def export_proved(out_dir, say=print, source=None):
    """REG-2630 - `heart2.py --export-proved DIR`: this machine's banked PROVENs that THIS checkout's bytes still key, into
    DIR/.heart2_cache.json with an `export` manifest (HEAD, clean), for another machine's `--import-proved`. The box
    proves the exact commit the Mac will push (`HEART2_CACHE_PATH=<dir>/.heart2_cache.json heart2 --prove <gates>
    --push`), exports, and the Mac imports. Only what peek() would serve leaves; an entry these bytes key differently
    (proved over other bytes) is left behind and counted. Refuses a dirty checkout, an unknown HEAD and an existing
    file (an export is one commit's, never merged into another's). -> exit code: 0 written, 2 refused"""
    import proof_shard as _PS
    source = source or CACHE
    ok_h, head = _git("rev-parse", "HEAD")
    head = head.strip() if ok_h else ""
    ok_d, dirty = _tracked_dirty()
    out = os.path.join(os.path.abspath(out_dir or "."), os.path.basename(CACHE))
    why = None
    if not head:
        why = "this checkout's HEAD is UNKNOWN"
    elif not ok_d or dirty.strip():
        why = "this checkout's tracked files differ from its HEAD (or git could not say), so its keys are not HEAD's"
    elif os.path.exists(out):
        why = "%s already exists - an export is one commit's, never merged into an older one" % out
    body = None
    if why is None:
        body, rwhy = _read_store(source, _entries_shape)
        if body is None:
            why = "%s is unreadable (%s)" % (source, rwhy)
    if why is not None:
        say("  ✗ REG-2630 EXPORT REFUSED: %s. Nothing was written." % why)
        return 2
    keyer = _shard_keyer(source)
    take, stale, other = {}, 0, 0
    for key, e in (body.get("entries") or {}).items():
        if not _PS.servable(e):
            other += 1
            continue
        if keyer(str(e.get("gate")), e.get("proof")) != key:
            stale += 1
            continue
        take[key] = e
    if not os.path.isdir(os.path.dirname(out)):
        os.makedirs(os.path.dirname(out))
    m = _PS.export_manifest(head, False, len(take), int(time.time() * 1000), runtime=export_runtime())   # REG-3045
    w_ok, w_why = _StoreFile(out, say).commit(lambda _disk: {"format": 2, "entries": take, "export": m})
    if not w_ok:
        say("  ✗ REG-2630 EXPORT REFUSED: %s could not be written (%s)." % (out, w_why))
        return 2
    say("  ✓ REG-2630 EXPORTED %d PROVEN entr(ies) keyed at HEAD %s into %s; %d banked over other bytes and %d not "
        "servable left behind. Import it on the pushing machine, at this same HEAD: heart2.py --import-proved <file>"
        % (len(take), head[:12], out, stale, other))
    return 0


def import_proved(paths, say=print, target=None, carried=None, platform=None):
    """REG-2630 - `heart2.py --import-proved FILE...`: PROVENs proved ELSEWHERE (a box export, or census shard files -
    a partial set too) into this machine's verdict cache, served by the next push exactly like its own.

    THE ONE RULE: an entry is banked only under the key THIS checkout's bytes give its (gate, proof) - recomputed here,
    never read from the file - so it can only ever be served where the push would have proved those very bytes. An
    entry filed under any other key (other bytes, another commit, a tampered file) is DROPPED and named; a file of
    another HEAD, from a dirty tree, with no manifest, or into a dirty checkout is REFUSED whole. Each entry keeps the
    tree it was proved in, so REG-2599 still owes a clean run HERE to every gate whose law file the push changes.

    REG-3044 (#186): an entry whose proof - as THIS tree declares it - measured the other PC's venue, or an OS this one
    is not, is left out and named (proof_shard.carry_refusal), for every import. REG-3045: `carried` ({by, key}, from the
    proof carrier) marks a CARRIED import: its export must record the runtime it was proved under and match this PC's
    (proof_shard.runtime_refusal) or the whole file is refused, and every entry it banks says who carried it. `platform`
    is this PC's (sys.platform; a law's seam).
    -> exit code: 0 imported, 2 refused (nothing written)"""
    import proof_shard as _PS
    target = target or CACHE
    platform = platform or sys.platform
    ok_h, head = _git("rev-parse", "HEAD")
    head = head.strip() if ok_h else ""
    bodies = []
    for p in paths or []:
        body, why = _read_store(p, _entries_shape)
        bodies.append((os.path.basename(os.path.dirname(os.path.abspath(p))) + "/" + os.path.basename(p), body, why))
    ok, why, sets = _PS.check_proved(bodies, head)
    _man = {}                                # REG-3044 - file index -> its manifest (export or shard)
    for _i, (_lb, _bd, _w) in enumerate(bodies, 1):
        _m = ((_bd.get("export") or _bd.get("shard")) if isinstance(_bd, dict) else None)
        _man[_i] = _m if isinstance(_m, dict) else {}
    if ok and carried is not None:
        _rt = export_runtime()               # REG-3045 (D3) - a carried export is refused whole on its runtime
        for _i, (_lb, _bd, _w) in enumerate(bodies, 1):
            _rw = (_PS.runtime_refusal(_man[_i], _rt) if isinstance((_bd or {}).get("export"), dict)
                   else "it is not an export - only an export is carried")
            if _rw:
                ok, why = False, "%s was carried by %s and %s" % (_lb, carried.get("by") or "another PC", _rw)
                break
    if ok:
        ok_d, dirty = _tracked_dirty()
        if not ok_d or dirty.strip():       # REG-2630 - the importing checkout must BE its HEAD, or its keys are not
            ok, why = False, "this checkout's tracked files differ from its HEAD (or git could not say), so its keys are not HEAD's"
    _gone, _no, _src = [], [], {}
    if ok:
        _decl = _shard_decls()

        def _carry(i, e):                    # REG-3044 - THIS tree's declaration of the proof, never the file's
            _src[id(e)] = i
            pr = _decl(str(e.get("gate")), e.get("proof"))
            return _PS.carry_refusal(pr.get("needs") if isinstance(pr, dict) else None,
                                     _man.get(i, {}).get("platform"), platform)
        with _keys_prewarmed(target, sets, say=say):   # REG-3193 - the keys' parts computed on the spare cores first
            ok, why, take, skipped = _PS.select(sets, keyer=_shard_keyer(target), dropped=_gone, here=TREE_ID,
                                                refuse=_carry, refused=_no)
    if ok and carried is not None:           # REG-3045 - a carried entry says who carried it, under which key, from where
        _now = int(time.time() * 1000)
        for _e in take.values():
            _m = _man.get(_src.get(id(_e)), {})
            _e["carried"] = {"by": str(carried.get("by") or ""), "key": str(carried.get("key") or ""), "head": head,
                             "platform": _m.get("platform"), "at": _m.get("at"), "importedAt": _now}
    if not ok:
        say("  ✗ REG-2630 IMPORT REFUSED: %s. Nothing was written to %s." % (why, os.path.basename(target)))
        return 2
    out = {}

    def merge(disk):
        ent, added = _PS.merge_into((disk or {}).get("entries"), take)
        out["added"], out["evicted"] = added, _cache_evict(ent, CACHE_MAX)
        body = dict((k, v) for k, v in (disk or {}).items() if k not in ("format", "entries"))
        body.update(format=2, entries=ent)
        return body
    ok_w, why_w = _StoreFile(target, say).commit(merge)
    if not ok_w:
        say("  ✗ REG-2630 IMPORT REFUSED: %s could not be written (%s)." % (os.path.basename(target), why_w))
        return 2
    say("  ✓ REG-2630 IMPORTED %d file(s) proved elsewhere at HEAD %s: %d PROVEN entr(ies) banked, %d already served "
        "here and kept, %d not servable, %d DROPPED (keyed over other bytes)%s. A gate whose law file this push changes "
        "still runs clean here once (REG-2599)." % (len(sets), head[:12], out.get("added", 0),
                                                    len(take) - out.get("added", 0), skipped, len(_gone),
                                                    (", %d evicted over the cap" % out["evicted"]) if out.get("evicted") else ""))
    if _gone:
        _dg = {}
        for _s, _g, _i in _gone:
            _dg.setdefault(_g, []).append(_i)
        say("    ⚠ REG-2630 DROPPED, never banked - this checkout's bytes key them differently, so a push proves them: %s"
            % "; ".join("%s %s" % (g, sorted(v, key=str)[:6]) for g, v in sorted(
                _dg.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12]))
    if _no:
        _dw = {}
        for _s, _g, _i, _w in _no:
            _dw.setdefault(_w, []).append("%s[%s]" % (_g, _i))
        say("    ⚠ REG-3044 %d PROVEN entr(ies) NOT CARRIED - each measured something of the PC or the OS that proved it, "
            "so this PC judges it itself: %s" % (len(_no), "; ".join("%s (%s)" % (w, ", ".join(sorted(v)[:4]))
                                                               for w, v in sorted(_dw.items()))))
    if carried is not None:                  # REG-3045 - the carrier's one line, read back as the take's `banked`
        say("  REG-3045 CARRIED from %s: %d banked · %d already here · %d dropped · %d not carried"
            % (carried.get("by") or "another PC", out.get("added", 0), len(take) - out.get("added", 0), len(_gone),
               len(_no)))
    return 0


def prove_exit_code(results):
    """(exit_code, broken, idle) for a set of prove() verdicts. Decides; prints nothing.

    ══ v3292 — THE VERDICT MUST BE RETURNED, NOT ONLY PRINTED ═══════════════════════════════
    BLIND already exited 1 and that was right. INVALID did not — and INVALID is the verdict that
    says the sabotage MATCHED NOTHING, so the proof changed no byte and demonstrated nothing. The
    gate it belongs to has no working red-proof at all, while reporting that it has one.

    MEASURED 2026-09-18 with a throwaway gate whose `find` was deliberately absent:
        "INVALID — the tamper matched 0 time(s)"  ->  exit 0
    Twice in one session a REAL proof went INVALID because its anchor had rotted — once on a line
    my own refactor had deleted. Both printed the word and exited 0, so any hook or CI step
    calling this recorded success. That is how inert proofs accumulate precisely where the static
    law cannot see them. [[matches-once-can-still-prove-nothing]] [[exit-status-of-the-block]]

    ⚠ UNPROVABLE is NAMED AND NOT FAILED, deliberately. It means the law was already red before
    the tamper — a fact about the working tree, which the suite is the organ to report. Failing it
    here would make this tool red for something it did not find, and a tool that is red for
    somebody else's reason is one you learn to ignore.

    ⚠ #42 — THE ONE EXCEPTION IS --push, AND IT IS NOT DECIDED HERE. In `--prove --push` (hooks/pre-push's run) an
    UNPROVABLE whose law was ALREADY RED untampered STOPS the run, like a BLIND or an INVALID, and main() then exits 1 on
    the stop even though this function returns 0 for that UNPROVABLE: every proof after the stop was never run, and
    exit 0 would pass them unseen. So at push time a clean-run red REFUSES the push. An UNPROVABLE that could not judge
    at all (a deadline, a missing file) does not stop the run and is still named and not failed, push or not.

    Extracted from main() so it can be exercised with fixtures: a decision that can only be
    reached by building a sandbox is a decision nothing will ever test.
    """
    broken = sorted(n for n, v in (results or {}).items() if v in (BLIND, INVALID))
    idle = sorted(n for n, v in (results or {}).items() if v == UNPROVABLE)
    return (1 if broken else 0), broken, idle


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--prove", nargs="*", default=None)
    ap.add_argument("--push", action="store_true",
                    help="#42 push-time proving, what hooks/pre-push runs: declared 'widths' restrict a proof's runs, the "
                         "likeliest failures run first and the run stops at the first; one browser gate at a time")
    ap.add_argument("--changed", action="store_true",
                    help="#242 add the push's own changed-law set (the hook's rule) to --prove - the pre-flight")
    ap.add_argument("--changed-gates", action="store_true",
                    help="#242 print the push's changed-law set, one line, and exit")
    ap.add_argument("--reuse", action="store_true",
                    help="#186 the self-prove lane's census: serve a PROVEN banked over byte-identical inputs and bank "
                         "what it proves (his ruling 2026-10-28). A plain --prove never opens the cache")
    ap.add_argument("--slice", action="store_true",
                    help="#99 prove these gates as ONE SLICE of a census: the verdicts merge, and the gate fingerprint "
                         "is stamped only once no declaring gate is owed (self_prove's runs on a PC he plays on)")
    ap.add_argument("--trust", action="store_true",
                    help="REG-3191 the trust pass alone: write into the census every owed gate whose every proof the "
                         "bank serves over these bytes (no law runs); after --import-shards / --import-proved, run it "
                         "once the import lands")
    ap.add_argument("--net", action="store_true",
                    help="REG-3192 the SAFETY NET: prove these trusted gates on this PC (never another tree's word) and "
                         "record only what it finds (netFinds) - never the census's verdicts (self_prove's idle runs)")
    ap.add_argument("--detect", action="store_true")
    ap.add_argument("--ratchet", action="store_true")
    ap.add_argument("--triage", action="store_true",
                    help="split the no-red-proof gates into WRITABLE vs NOT PROVABLE HERE")
    ap.add_argument("--forecast", nargs="*", default=None,
                    help="REG-2353 print the '#42 FORECAST' block for these gates - what a --push run will reuse, narrow "
                         "and run in full, and what can never be banked - BEFORE any proving; always exits 0")
    ap.add_argument("--pushes", nargs="?", type=int, const=20, default=None,
                    help="REG-2353 print this machine's last N push records (forecast vs actual), newest last")
    ap.add_argument("--proof-shard", default=None, metavar="K/N",
                    help="REG-2585 with --push: prove only shard K of N of these gates' proofs (one plan every shard "
                         "computes alike), into the fresh cache file HEART2_CACHE_PATH names; no census is written")
    ap.add_argument("--plan-shards", action="store_true",
                    help="v3891 (#194) print how many proof shards THIS commit's owed proofs need (n=, list=) from the same "
                         "inputs every shard plans from (HEART2_SHARD_SERVED, HEART2_SHARD_COSTS) and exit 0; proves nothing")
    ap.add_argument("--target-s", type=float, default=None, help="v3891 (#194) with --plan-shards: the slowest prove a shard may model")
    ap.add_argument("--min-shards", type=int, default=None, help="v3891 (#194) with --plan-shards: the fewest shards")
    ap.add_argument("--max-shards", type=int, default=None, help="v3891 (#194) with --plan-shards: the most shards")
    ap.add_argument("--fallback-shards", type=int, default=22,
                    help="v3891 (#194) with --plan-shards: the count a round runs at when the plan cannot be cut")
    ap.add_argument("--output", default=None, metavar="FILE",
                    help="v3891 (#194) with --plan-shards: append n= and list= to this file (GitHub's GITHUB_OUTPUT)")
    ap.add_argument("--merge-red", nargs="+", default=None, metavar="FILE",
                    help="v3891 (#194) merge these shards' red memories into --red-out for the next round's seed; exits 0")
    ap.add_argument("--red-out", default=None, metavar="FILE", help="v3891 (#194) with --merge-red: the merged memory")
    ap.add_argument("--import-shards", nargs="+", default=None, metavar="FILE",
                    help="REG-2586 merge every shard's banked PROVENs into this machine's verdict cache - all shards of "
                         "this HEAD or nothing; each entry keeps its tree; exits 2 on a refusal")
    ap.add_argument("--export-proved", default=None, metavar="DIR",
                    help="REG-2630 write this machine's PROVENs that HEAD's bytes still key into DIR/.heart2_cache.json "
                         "with an export manifest, for --import-proved on the pushing machine; exits 2 on a refusal")
    ap.add_argument("--import-proved", nargs="+", default=None, metavar="FILE",
                    help="REG-2630 bank PROVENs proved elsewhere (a box export or census shard files, partial allowed) "
                         "of THIS HEAD, each only under the key this checkout's bytes give it; exits 2 on a refusal")
    ap.add_argument("--carried-by", default=None, metavar="OWNER",
                    help="REG-3045 with --import-proved: the file was CARRIED from this roster owner's PC (proof_carrier) - "
                         "its runtime must match this PC's and every banked entry says who carried it")
    ap.add_argument("--carried-key", default=None, metavar="KEYID",
                    help="REG-3045 with --carried-by: the roster key the carrier verified the export under")
    ap.add_argument("--import-parent", default=None, type=int, metavar="PID",
                    help="#103 with --import-shards: the console that asked for the import; the import ends when it is "
                         "gone (_watch_import_parent)")
    ap.add_argument("--import-progress", default=None, metavar="FILE",
                    help="REG-3194 with --import-shards: keep {done, of, etaS, at, phase} in FILE while the keys are "
                         "computed (proof_release's console import reads it)")
    a = ap.parse_args(argv)
    if a.import_shards is not None:
        if a.import_parent:
            _watch_import_parent(a.import_parent)    # #103 - an import never outlives the console that asked for it
        _irc = import_shards(a.import_shards, progress=a.import_progress, trust=a.trust)
        if _irc == 0 and a.trust:
            trust_now()                          # REG-3191 - the import's proofs open the locks now, not at idle
        return _irc
    if a.export_proved is not None:
        return export_proved(a.export_proved)
    if a.import_proved is not None:
        _irc = import_proved(a.import_proved, carried=({"by": a.carried_by, "key": a.carried_key}
                                                       if a.carried_by else None))
        if _irc == 0 and a.trust:
            trust_now()                          # REG-3191 - a carried import opens the locks the same way
        return _irc
    if a.trust and a.prove is None:
        return trust_now()                       # REG-3191 - the lane's light start: the trust pass alone
    if a.plan_shards:
        return plan_shards(a.target_s, a.min_shards, a.max_shards, a.fallback_shards, a.output)
    if a.merge_red is not None:
        if not a.red_out:
            ap.error("--merge-red needs --red-out FILE")
        return merge_red_files(a.merge_red, a.red_out)
    _SHARD["spec"] = None
    if a.proof_shard is not None:
        import proof_shard as _PS
        _sw = None
        try:
            _SHARD["spec"] = _PS.parse_spec(a.proof_shard)
        except ValueError as _se:
            _sw = str(_se)
        if _sw is None and not (a.prove is not None and a.push):
            _sw = "--proof-shard proves through --prove --push, the only run that banks"
        if _sw is None and not os.environ.get("HEART2_CACHE_PATH"):
            _sw = "--proof-shard needs HEART2_CACHE_PATH: a shard banks into a file of its own, never this machine's store"
        if _sw is None and str(os.environ.get("HEART2_PROVE_CACHE", "1")).strip().lower() in ("0", "no", "off", "false"):
            _sw = "--proof-shard with the cache OFF would bank nothing"
        if _sw is None and os.path.exists(CACHE):
            _sw = ("%s already exists - a shard's own file starts empty, so it holds only what this run serves or proves "
                   "(REG-2961: earlier proofs come in read only, through HEART2_SHARD_SEED)" % CACHE)
        if _sw is not None:
            _SHARD["spec"] = None
            print("  ✗ REG-2585: %s" % _sw)
            return 2
    if a.forecast is not None:
        return _forecast_main(a.forecast)
    if a.pushes is not None:
        return _pushes_main(a.pushes)
    if a.changed_gates or a.changed:
        _names, _base, _cwhy = changed_gates()
        if _cwhy:
            print("  #242 %s" % _cwhy)
            if a.changed_gates:
                return 2
        if a.changed_gates:
            print(" ".join(_names))
            return 0
        print("  #242 the push's changed-law set (since %s): %d gate(s)" % (_base, len(_names)))
        a.prove = list(a.prove or []) + _names
        if not a.prove:
            print("  nothing changed since %s - nothing to pre-flight" % _base)
            return 0
    if a.prove is not None:
        # a killed prover removes its sandboxes; and the ones an EARLIER killed run left are swept first
        install_sandbox_cleanup()
        for _p, _why in sweep_stale_sandboxes():
            print("  swept a sandbox an interrupted run left behind (%s): %s" % (_why, os.path.basename(_p)))
    if a.triage:
        triage()
        return 0
    if not any([a.report, a.prove is not None, a.detect, a.ratchet]):
        a.report = True

    census, results, hits = {}, {}, []
    _stopped = []
    _PROVE_UNMATCHED[:] = []                    # REG-2352 - this run's names only, never a previous run's
    _PUSH_RECORD["record"] = None               # REG-2353 - this run's record only

    def _done(code):
        """REG-2353 - a --push run's record, with its exit, is written whatever the exit; the hook deletes its log."""
        _rec = _PUSH_RECORD.get("record") if (a.prove is not None and a.push) else None
        if isinstance(_rec, dict):
            _c, _b, _i = prove_exit_code(results)
            _rec.update({"exit": code, "broken": _b, "idle": _i, "unmatched": [n for n, _w in _PROVE_UNMATCHED]})
            try:
                import prove_record as _PR
                _at = _PR.append(_rec, where=_PR.path(cache_path=CACHE), say=print)
            except Exception as _we:
                _at = None
                print("  #42 RECORD (REG-2353): not written (%s) - this run's account is only in this log"
                      % type(_we).__name__)
            if _at:
                print("  #42 RECORD (REG-2353): this run's forecast vs actual is kept in %s (per machine; "
                      "`python3 tv/heart2.py --pushes` reads it) - it outlives this log" % os.path.basename(_at))
        return code
    if a.report or a.ratchet:
        census = report()
    if a.prove is not None:
        print("")
        if a.push:
            results = prove(only=set(a.prove) or None, push=True, stopped=_stopped)
        else:
            _rk = {"reuse": True} if a.reuse else {}     # #186 - the flag travels only when the lane set it
            if a.net:
                _rk["net"] = True                          # REG-3192 - only named gates: the net never proves a census
            if a.net and not a.prove:
                print("  ✗ REG-3192 --net proves named trusted gates only - name them (self_prove does)")
                return 2
            results = (prove(only=set(a.prove) or None, stamp=False, **_rk) if a.slice
                       else prove(only=set(a.prove) or None, **_rk))
    if a.detect:
        print("")
        hits = detect()
    if census or results or hits:
        p = propose(results, census, hits)
        # v3886 (#107, windows-latest: "ValueError: path is on mount '\\\\.\\nul', start on mount 'D:'") - on Windows a path
        # on another drive has no path relative to the repo; a finished run must never die on the line that names its file
        try:
            _pw = os.path.relpath(p, REPO)
        except ValueError:
            _pw = p
        print("\n  proposals written to %s (it never edits a guard)" % _pw)

    if a.ratchet:
        # ⚠ SAME RULE AS _write_state: an unreadable ledger is UNKNOWN, not an empty one. The
        # ratchet compares against `prev`; reading a broken file as {} would make every gate look
        # newly proven and the comparison meaningless. [[unknown-stays-unknown]]
        prev = {}
        if os.path.exists(STATE):
            try:
                with io.open(STATE, encoding="utf-8") as fh:
                    prev = json.load(fh)
            except Exception as _e:
                print("  ⚠ %s exists but would not parse (%s) — the ratchet has nothing to compare "
                      "against, so it reports UNKNOWN rather than a clean run."
                      % (os.path.basename(STATE), type(_e).__name__))
                return 2
        # ⚠⚠ A BROKEN PARSER MUST NOT PRODUCE A GREEN LOCK. If run_gates will not import,
        # gate_files() returns [] and the census reads total=0, unproven=0 — which sails past the
        # ratchet AND writes a baseline of 0 that every honest run afterwards fails forever, so
        # the fix would look like the regression. This is the same zero-with-no-denominator the
        # file already recorded making once, one function along. [[zero-needs-a-denominator]]
        if int(census.get("total") or 0) < 100:
            print("\n  ✗ RATCHET REFUSED: the census found %s gate(s). run_gates registers "
                  "hundreds, so this is the parser failing, not a clean tree. UNKNOWN is not a "
                  "pass, and a baseline written from it would poison every later run."
                  % census.get("total"))
            return 1
        base = int(prev.get("unproven", 10 ** 9))
        now = int(census.get("unproven", 0))
        if now > base:
            print("\n  ✗ RATCHET: unproven went %d → %d. A new gate must arrive with its proof."
                  % (base, now))
            return 1
        # ⚠⚠ v2853 — THIS WROTE A TWO-KEY DICT OVER THE WHOLE CENSUS, AND THE SCAR ABOVE SAYS SO
        # ALREADY: "`--ratchet` wrote a two-key dict that dropped `blind` entirely, flipping a DARK
        # heart back to WATCHED". That was fixed in the prove path and left standing HERE.
        # MEASURED 2026-09-09 in a sandbox, with a baseline loose enough for the ratchet to pass:
        #     keys 10 -> 2 · provedGates 97 -> 0 · verdictAt 45 -> 0 · blind/declared/partial gone
        #     proved 97 -> 98, the verified count replaced by the DECLARATION count
        # One --ratchet erased every proof the heart had ever banked. MERGE, NEVER CLOBBER — and do
        # not write `proved` from the census at all, because report() counts declarations.
        # [[the-unjoined-end]] [[label-outlived-referent]]
        _out = dict(prev)
        _out["unproven"] = now
        with io.open(STATE, "w", encoding="utf-8") as fh:
            json.dump(_out, fh)
        print("\n  ✓ RATCHET: unproven %d (was %s)" % (now, base if base < 10 ** 9 else "unset"))
    # ══ v3292 — AN INERT PROOF MUST NOT EXIT 0 ═══════════════════════════════════════════════
    # BLIND already returned 1 and that was right. INVALID did not, and INVALID is the verdict
    # that says the sabotage MATCHED NOTHING — the proof changed no byte, so it demonstrated
    # nothing and the gate it belongs to has no working red-proof at all.
    #
    # MEASURED 2026-09-18 with a throwaway gate whose `find` was deliberately absent:
    #     "INVALID — the tamper matched 0 time(s)"  ->  exit 0
    # Twice in one session a real proof went INVALID because its anchor had ROTTED — once on a
    # line my own refactor had deleted. Both printed the word and exited 0, so any harness, hook
    # or CI step calling this would have recorded success. That is how inert proofs pile up
    # exactly where the static law cannot see them. [[matches-once-can-still-prove-nothing]]
    # [[exit-status-of-the-block]]
    #
    # ⚠ UNPROVABLE is deliberately NOT failed here. It means the law was ALREADY RED before the
    # tamper, which is a fact about the working tree, and the test suite is the organ that reports
    # that. Failing it twice would make this tool red for a reason it did not find.
    if results:
        _code, _broken, _idle = prove_exit_code(results)
        if _idle:
            print("\n  ⚪ %d gate(s) UNPROVABLE — already red before the tamper, so nothing was "
                  "demonstrated. Not failed here: that is the suite's finding, not this one.\n     %s"
                  % (len(_idle), ", ".join(_idle[:6]) + (" …" if len(_idle) > 6 else "")))
        if _broken:
            print("\n  ✗ %d gate(s) have a red-proof that PROVES NOTHING (blind or inert):\n     %s"
                  % (len(_broken), ", ".join(_broken[:8]) + (" …" if len(_broken) > 8 else "")))
        if _code:
            return _done(_code)
    # #42 — A STOPPED PUSH-TIME RUN IS A REFUSAL even when what stopped it is not failed above (a law ALREADY RED
    # untampered is UNPROVABLE): the proofs after it were never run, and exit 0 would pass them unseen.
    if _stopped and _SHARD.get("spec"):
        print("\n  ✗ REG-2591 this proof shard OWES %d failure(s) (%s) — it kept going, so every other proof ran and was "
              "banked, but it cannot pass." % (len(_stopped), ", ".join("%s[%d] %s" % tuple(f[:3]) for f in _stopped[:4])
                                               + (" …" if len(_stopped) > 4 else "")))
        return _done(1)
    if _stopped:
        _n, _i, _v, _why = _stopped[0]
        print("\n  ✗ #42 the push-time run STOPPED at %s[%d] (%s: %s) — the proofs after it were NOT RUN, so this "
              "cannot pass." % (_n, _i, _v, _why))
        return _done(1)
    # REG-2352 (#42 R11) — A NAME THAT MATCHED NO GATE PROVED NOTHING, AND NOTHING PROVEN IS NEVER A PASS. It exited 0 and
    # said "nothing to prove": a typo, or `NAME[5]`, read as a proof that held.
    if a.prove is not None and _PROVE_UNMATCHED:
        print("\n  ✗ REG-2352: %d --prove name(s) matched no gate, so nothing was proven for them and this run cannot "
              "pass: %s" % (len(_PROVE_UNMATCHED), "; ".join("%s (%s)" % t for t in _PROVE_UNMATCHED[:6])))
        return _done(2)
    return _done(0)


def _forecast_main(names):
    """REG-2353 — `heart2.py --forecast NAMES...`: the "#42 FORECAST" block, and exit 0 whatever happens."""
    try:
        gates = gate_files(say=lambda *a, **k: None)
        want = set(names or ())
        todo = gates_named(want, gates) if want else []      # REG-2352 - the one predicate prove() and unmatched ask
        have = [(n, f, red_proofs_in(f)) for n, f in todo]
        forecast([(n, f, p) for n, f, p in have if p], say=print,
                 unmatched=unmatched_names(want, gates) if want else ())
    except Exception as e:
        print("  #42 FORECAST: UNKNOWN - %s: %s" % (type(e).__name__, str(e)[:120]))
    return 0


def _pushes_main(n):
    """REG-2353 — `heart2.py --pushes [N]`: this machine's last N push records. -> 0, or 2 when they cannot be read"""
    import prove_record as _PR
    where = _PR.path(cache_path=CACHE)
    recs, bad = _PR.read(where, n=n)
    if recs is None:
        print("  #42 PUSH RECORDS: UNKNOWN - %s (%s)" % (bad, os.path.basename(where)))
        return 2
    print("  #42 PUSH RECORDS: the last %d of this machine's --push runs (%s)%s"
          % (len(recs), os.path.basename(where), (" - %d line(s) would not parse" % bad) if bad else ""))
    for line in _PR.table(recs):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
