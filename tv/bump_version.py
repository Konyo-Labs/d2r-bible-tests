#!/usr/bin/env python3
"""v1489 — stamp a new version across the four surfaces that carry one.

Usage: python bump_version.py v<N> <short name> <note...>   (the leading 'v' is required)

The version lives in four places: the board's `D2R_BUILD`, `control_app.py`'s `/api/status`,
`tv_diablo.py`'s `VERSION`, and `tv/WINDOWS_SHIP.json`. Bumping them by hand is four chances to
miss one, and a half-bumped tree is not cosmetic — `test_button_matrix` compares the LIVE app's
version to the ship manifest, so a missed stamp surfaces as "the running app is a different build
than the tree you are testing" and sends the next person hunting a phantom.

The same bible.html write also moves the <title> version token and the d2r-build,
d2r-build-date and d2r-build-note metas. Those tags are not a fifth file. Left alone,
the browser tab and the raw page keep an old version while window.D2R_BUILD moves.

The board note is a SINGLE-QUOTED JS literal. Writing one by hand during v1478 put an apostrophe in
"someone else's chronicle", which terminated the string early and threw a SyntaxError that blanks
the entire 37k-line page. The syntax gate caught it — but the right place to stop that class is
before it is written, so this refuses an apostrophe outright rather than relying on the gate to
notice afterwards.

Each stamp is verified after writing: a silent no-op replace would leave the tree half-bumped,
which is the exact failure this tool exists to prevent.
"""
import ast, datetime, io, json, os, re, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# v1489 — this tool prints, so it must survive the operator's console (REG-044/054/077/078).
# Caught by TestToolsCanReportTheirVerdict on its first run, which is the gate doing its job.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass


def _parses_as_page(html_text, label="bible.html"):
    """Parse the ARTIFACT THAT WILL HIT DISK, through the SAME <script> extractor the gate uses.

    ⚠⚠ v3104 — CHECKING THE LINE WAS NOT CHECKING THE FILE, and a cross-family read of v3103 found
    the hole the same night it shipped. `note` lands inside a `<script>` block, so a note
    containing `</script>` is PERFECTLY VALID JAVASCRIPT in isolation and still ends the block.
    Measured:

        _parses_as_js("... note:'closed the </script> tag' };")   -> None      (valid JS)
        the extractor then feeds node:  "(function(){ ... note:'closed the "  (unterminated)

    An unterminated string and an unclosed IIFE — the board blanks. That is the v1478 apostrophe
    failure wearing an HTML tag instead of a quote, and it walked straight past a guard written
    the same day to stop exactly this class. Two checks that are each correct, never meeting at
    the artifact. `</SCRIPT>` and `</script >` take the same path.
    [[the-unjoined-end]] [[source-reading-guard]]

    ⚠ ONE EXTRACTOR. It writes the pending text to a temp root and points `js_syntax_gate` at it,
    rather than growing a second `<script>` regex here. [[copy-drift]]

    -> a problem string, or None (None also means UNMEASURED — `_preflight` says so out loud).
    """
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="bumpcheck-")
    try:
        with io.open(os.path.join(d, label), "w", encoding="utf-8") as fh:
            fh.write(html_text)
        sys.path.insert(0, os.path.join(REPO, "tv"))
        import js_syntax_gate as _js
        _old = _js.REPO
        try:
            _js.REPO = d
            probs, why = _js.check_with_node([label])
        finally:
            _js.REPO = _old
        if why:
            return None                    # cannot measure is not the same as broken
        return "; ".join(probs) if probs else None
    except Exception:
        return None
    finally:
        shutil.rmtree(d, True)


def _preflight(repo=None):
    """Refuse to stamp a tree that does not PARSE. Raises SystemExit; writes nothing.

    ⚠⚠ v3103 — THE CHOKE POINT HAD NO CHECK, AND I PUT A SyntaxError ON HIS SCREEN THROUGH IT.
    On 2026-09-14 a splice left a bare `} catch(e){}` in bible.html. I then ran this tool, which
    happily stamped v3100 onto a file the browser refuses to parse — and because HIS CONSOLE EXECS
    THE WORKING TREE, `window.renderSubMeter` was never assigned on his live screen until the
    second eye found it on the shipped diff. The gate that catches exactly this (`js-syntax`,
    registered in run_gates) already existed. I did not run it. A law nobody runs is a law nobody
    applied. [[carved-skill-unloaded-is-unapplied]] [[execs-the-working-tree]]

    ⚠ THIS BELONGS HERE RATHER THAN IN ANOTHER GATE. The version bump is the ONE door every change
    passes through — four stamps move together or none do — and it is the moment the tree becomes
    something he executes. The block below already promises "nothing touches disk until all four
    are known good"; until now "known good" meant only that a regex matched. Parsing is what that
    sentence was always claiming. [[the-unjoined-end]]

    ⚠ AND IT REUSES `js_syntax_gate`, never a second copy of the block extractor. One parser, one
    vocabulary. [[copy-drift]]
    """
    # ⚠ v3103b — A ROOT, BECAUSE OTHERWISE THE LAW CANNOT SEE ITS OWN DEFEAT. Two red-proofs came
    # back BLIND: disabling a check that would have PASSED anyway changes nothing observable, so
    # the only way to prove this guard can fire is to hand it a tree that is genuinely broken —
    # which means a temp copy, which means a root. [[feedback-blind-fixture-green-gate]]
    repo = repo or REPO
    bad = []
    for rel in ("tv/control_app.py", "tv/tv_diablo.py"):
        try:
            ast.parse(io.open(os.path.join(repo, rel), encoding="utf-8").read())
        except SyntaxError as e:
            bad.append("%s: %s (line %s)" % (rel, e.msg, e.lineno))
    try:
        json.load(io.open(os.path.join(repo, "tv", "WINDOWS_SHIP.json"), encoding="utf-8"))
    except Exception as e:
        bad.append("tv/WINDOWS_SHIP.json: %s" % e)
    try:
        sys.path.insert(0, os.path.join(REPO, "tv"))
        import js_syntax_gate as _js
        # ⚠ ONE PARSER, FILES FROM THE GIVEN ROOT. The module is imported once from this repo —
        # never copied — and only the root it reads from is redirected. [[copy-drift]]
        _old_root = _js.REPO
        try:
            _js.REPO = repo
            probs, why = _js.check_with_node(["bible.html"])
        finally:
            _js.REPO = _old_root
        if why:
            # ⚠ A SKIP IS NOT A PASS, and it says which half went unmeasured rather than implying
            # the file is fine. [[unknown-stays-unknown]]
            print("   \u26a0 bump preflight could NOT parse bible.html (%s) — its syntax is "
                  "UNMEASURED for this stamp, not clean" % why, flush=True)
        bad.extend(probs)
    except Exception as e:
        print("   \u26a0 bump preflight could not run the JS parser (%s) — bible.html syntax is "
              "UNMEASURED for this stamp" % type(e).__name__, flush=True)
    if bad:
        raise SystemExit(
            "refusing to stamp a tree that does not parse — NOTHING WRITTEN.\n   "
            + "\n   ".join(bad)
            + "\n   His console EXECS this working tree, so a stamped broken file is a broken "
              "console. Fix the parse error, then bump.")


def _heart_gate(note, repo=None):
    """A version that changes a SURFACE must also change what WATCHES it. -> None, or SystemExit.

    ⚠⚠ HIS STANDING ORDER, 2026-09-06: JOIN -> GATE -> HEART -> BANK, every fix. It is carved in
    memory as `join_gate_heart`. ON 2026-09-16 I READ THAT SCAR AND THEN SKIPPED HEART ON FIVE
    CONSECUTIVE VERSIONS — v3201 through v3205 — shipping laws, gates and BUGS entries for the
    sweep meter, the river fold, the station chips, the TOMBSTONE vocabulary and the fleet rows,
    with ZERO doctor, health-engine or corroborator coverage for any of them. Measured when he
    asked: `stationbar 0 · sh-filterfold 0 · shr-stkey 0 · sweep-box 0 · fleet-row 0`, against
    402 registered gates and 61 doctor rows.

    His answer: *"are you kidding me!? make this a scar going forward.. we will kep backtracking
    this way."* He is right, and the deeper point is that THE SCAR ALREADY EXISTED AS PROSE AND
    DID NOT HOLD. Writing another paragraph would be the same failure with more words, so it
    becomes mechanical, at the one choke point no ship can go around.
    [[carved-skill-unloaded-is-unapplied]] [[heart-v2-instruments-watch-themselves]]

    WHY A GATE AND NOT A TEST: a test fails when the code CHANGES. The thing being prevented here
    is a surface that changes while its supervision does NOT — which is invisible to every test in
    the tree, because nothing is broken. Only the bump sees both halves at once.

    ⚠ IT CAN BE PASSED, BUT NEVER SILENTLY. `HEART: <reason>` in the note is an explicit recorded
    decision that lands in the version row, the commit and BLUEPRINT.md — the same shape as every
    other lock here. A copy edit genuinely needs no new heart row; saying so out loud costs six
    words and leaves the reasoning where the next person can judge it.

    ⚠ AND IF THE CHECK CANNOT RUN IT MUST NOT BLOCK. An unavailable git is UNKNOWN, not a
    violation — a gate that fails closed on its own plumbing would cost a version stamp for a
    reason that has nothing to do with the heart. [[unknown-stays-unknown]]
    """
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    # ⚠ #223 — GRADE THE TREE BEING BUMPED, NOT THIS FILE'S OWN. `bump(repo=...)` stamps the tree it
    # is handed, and this ran `git diff` beside the script regardless — so a bump aimed at a temp
    # tree was refused for uncommitted edits in the LIVE repo (test_the_bump_refuses_a_tree_that_
    # does_not_parse went red whenever the real tree held a surface edit). A tree with no git is
    # UNKNOWN and does not block, as below.
    if repo:
        here = os.path.join(os.path.abspath(repo), "tv")
    SURFACES = ("tv/control_ui.html", "bible.html")
    WATCHERS = ("tv/console_doctor.py", "tv/health_engine.py", "tv/corroborate.py",
                "tv/heart2.py")
    try:
        r = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                           cwd=os.path.dirname(here), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode != 0:
            return                                  # cannot see the tree: UNKNOWN, never a block
        touched = set(x.strip() for x in (r.stdout or "").splitlines() if x.strip())
    except Exception:
        return                                      # same: the check failing is not a violation
    if not touched:
        return
    surf = sorted(f for f in touched if f in SURFACES)
    if not surf:
        return
    watch = sorted(f for f in touched if f in WATCHERS)
    if watch:
        print("   heart: %s changed alongside %s" % (", ".join(watch), ", ".join(surf)))
        return
    if "HEART:" in note:
        print("   heart: exempted by an explicit HEART: note — recorded in the version row")
        return
    raise SystemExit(
        "\n  REFUSED — this version changes %s and changes nothing that WATCHES it.\n"
        "  His standing order is JOIN -> GATE -> HEART -> BANK. A gate fails when code changes;\n"
        "  a heart says a surface is unsupervised even when nobody touched it, and that is the\n"
        "  half that keeps going missing (v3201-v3205 shipped five surfaces with zero heart rows).\n"
        "\n  Do ONE of these:\n"
        "    1. add or update a row in %s\n"
        "    2. put `HEART: <why this surface needs no watcher>` in the note — it is recorded,\n"
        "       not waived, and lands in the version row and the commit.\n"
        % (", ".join(surf), " / ".join(w.split("/")[-1] for w in WATCHERS)))


_HEAD_VER = re.compile(r"v\d+(?:\.\d+)*")


def _attr_text(note):
    """Put the build note in a double-quoted meta attribute without breaking it.

    D2R_BUILD.note is a single-quoted JS literal: an apostrophe is already refused, and a
    double quote is legal there. The same quote ends content="...". An ampersand or a
    left angle bracket would rewrite the attribute. The JS note is stored unchanged.
    """
    if "\n" in note or "\r" in note:
        raise SystemExit(
            "the note spans a line, so the d2r-build-note attribute would break — nothing written")
    safe = note.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    if '"' in safe or "\n" in safe or "\r" in safe:
        raise SystemExit("the d2r-build-note attribute would still break — nothing written")
    return safe


def _rewrite_head_stamps(html, ver, today, note):
    """Move the <title> version token and the three d2r-build metas. Each pattern once.

    Only the version token inside the existing title moves. The words around it stay.
    A missing tag, or a second one, refuses the bump before anything is written.
    """
    note_attr = _attr_text(note)

    def title_repl(m):
        body = m.group(1)
        versions = _HEAD_VER.findall(body)
        if len(versions) != 1:
            raise SystemExit(
                "the title holds %d version tokens — nothing written" % len(versions))
        return "<title>" + body.replace(versions[0], ver, 1) + "</title>"

    title_pat = re.compile(r"<title>([^<]*)</title>")
    titles = list(title_pat.finditer(html))
    if len(titles) != 1:
        raise SystemExit("the title matched %d times — nothing written" % len(titles))
    html = title_pat.sub(title_repl, html, count=1)

    def put(content):
        def repl(m):
            return m.group(1) + content + m.group(2)
        return repl

    specs = (
        (re.compile(r'(<meta name="d2r-build" content=")[^"]*(">)'), ver, "d2r-build"),
        (re.compile(r'(<meta name="d2r-build-date" content=")[^"]*(">)'), today, "d2r-build-date"),
        (re.compile(r'(<meta name="d2r-build-note" content=")[^"]*(">)'), note_attr, "d2r-build-note"),
    )
    for pat, content, label in specs:
        found = list(pat.finditer(html))
        if len(found) != 1:
            raise SystemExit("%s matched %d times — nothing written" % (label, len(found)))
        html = pat.sub(put(content), html, count=1)
    return html


# v3774 (REG-2295) — the name and note are published free text; tv/stamp_leak.py decides what may not be.
from stamp_leak import leak_problem, free_text_problem  # noqa: E402


def bump(ver, name, note, repo=None, items=None):
    # ⚠⚠ v3330 (#72) — DO NOT BANK A VERSION INTO A TREE SOMEONE IS GRADING.
    #
    # His ruling from the #46 false alarm: "do not write while a gate runs" must be a REFUSAL, not
    # a habit. It has existed as PROSE in CLAUDE.md, in regression-guard and in every staged
    # apply-script — four copies, none enforcing — and an entire session was spent hand-typing
    # `pgrep -f hooks/pre-push` before each write. That worked every time, which is exactly what a
    # habit looks like until the once it does not.
    #
    # WHY HERE: hooks/pre-push grades the WORKING TREE, not the commit (REG-1131). A version banked
    # mid-run earns a green verdict about bytes that are not the ones shipping — the most expensive
    # wrong answer this repo produces, because it is indistinguishable from a correct one. This is
    # the one chokepoint EVERY ship passes, so putting it here makes that case structurally
    # impossible even when the discipline slips.
    #
    # ⚠ IT CANNOT COVER AN AD-HOC EDIT and does not pretend to: a heredoc writing bible.html will
    # never consult a module it does not import. What it covers is the BANK step. [[the-unjoined-end]]
    try:
        import tree_busy as _tb
        _busy = _tb.why(repo or REPO)
    except Exception as _tbe:
        _busy = ("tree_busy could not be asked (%s) — that is UNKNOWN, not free"
                 % type(_tbe).__name__)
    if _busy:
        raise SystemExit(
            "REFUSED to bump %s: %s\n"
            "   Wait for it to finish, then bump again. Nothing has been written."
            % (ver, _busy))
    # REG-3778 (#200, 11-12) - A VERSION IS NOT BANKED WHILE A REGISTERED PROOF LAW HAS NO SHARD-TIMING ROW. Three versions
    # running (v3899 f1fd499a6, v3900 ac3eb1747, v3901 6c14c97f1) the pre-flight stopped on
    # test_the_shard_balance_file_covers_every_proof_test after the bump, and each paid a fix commit and a pre-flight
    # restart. The new laws are registered before the bump, so this is the moment to say it. UNKNOWN (the module or its
    # file will not read) refuses nothing - the law still holds the line.
    # REG-3804 (the v3902 second eye) - a timings file that IS there and will not read, or a check that raised, was as silent
    # as no file at all. It still refuses nothing (the law holds the line) - and now it says the check was UNKNOWN.
    _st_why = None
    try:
        import shard_timings as _st
        if os.path.isfile(_st.path(repo or REPO)) and _st.load(repo or REPO) is not None:
            _ok, _miss, _ = _st.coverage(root=repo or REPO)
        else:
            _ok, _miss = True, []          # no timings file here (a fixture repo) or it will not read: UNKNOWN
            if os.path.isfile(_st.path(repo or REPO)):
                _st_why = "tv/shard_timings.json is there and will not read"
    except Exception as _ste:
        _ok, _miss, _st_why = True, [], "the shard-timing check raised %s" % type(_ste).__name__
    if _st_why:
        print("⚠ REG-3804: %s - UNKNOWN, so this bump does not refuse on it; the pre-flight's shard-balance law still holds "
              "the line" % _st_why)
    if not _ok:
        raise SystemExit("REFUSED to bump %s: tv/shard_timings.json has no row for %d registered proof law(s) (%s%s) - run "
                         "`python3 tv/shard_timings.py --write`, commit it, then bump. Nothing has been written."
                         % (ver, len(_miss), ", ".join(_miss[:4]), " ..." if len(_miss) > 4 else ""))
    for _label, _txt in (("name", name), ("note", note)):
        _leak = leak_problem(_txt)
        if _leak:  # BUMP-LEAK-REFUSE
            raise SystemExit("REFUSED to bump %s: the %s carries %s, and it would be published in bible.html, "
                             "WINDOWS_SHIP.json and TASKS.md. Nothing has been written." % (ver, _label, _leak))
    if "'" in note or "'" in name:
        raise SystemExit("apostrophe in note/name would break the single-quoted D2R_BUILD literal")
    # REG-1689 - THE NAME IS THE BADGE'S WORDS, NEVER THE VERSION AGAIN. v3545-v3546 were bumped with the version as their
    # name, and the badge read "v3546 · 2026-10-01 · v3546" - CI's v1748 badge spec went red after the publish.
    _nm = str(name or "").strip().lower()
    if not _nm or _nm.startswith(str(ver).strip().lower()):
        raise SystemExit("the short name must say what %s DOES (e.g. \"one clock hour\"), never repeat the version - "
                         "the badge printed it twice (tests/v1748_build_badge_says_it_once.spec.ts)" % ver)
    # REG-1741 - AND THE NOTE NEVER OPENS WITH THE VERSION EITHER: this tool writes "vNNNN: <note>" into WINDOWS_SHIP and
    # "vNNNN — <note>" into TASKS, so a note that starts "v3561 — ..." printed "v3561: v3561 — ..." (v3554 and v3561,
    # caught by the #231 code seat on 065f5433).
    _nt = str(note or "").strip().lower()
    if _nt.startswith(str(ver).strip().lower()):
        raise SystemExit("the note must not open with %s - the tool prefixes it, and it printed twice in "
                         "WINDOWS_SHIP and TASKS (REG-1741)" % ver)
    _heart_gate(note, repo)

    # 2026-08-20 — AND A NOTE MAY NOT NAME A CSS TOKEN IN CALLABLE FORM.
    #
    # v1841 fixed a chip that referenced `var(--fs-tiny)`, a token this file never defines, and then
    # DESCRIBED the fix in the build note using that exact spelling. D2R_BUILD.note is a JS string
    # literal inside bible.html, and v1733's gate strips block comments but not string literals — so
    # it read the sentence about the token as a live reference to it and stayed red. The fix
    # re-created the very defect it fixed, one line further down. [[feedback-comments-vs-code]]
    #
    # Same shape as the apostrophe above: the note is DATA that lands in a parsed file, so what it
    # may contain is a property of the file and not of the prose. Write `--fs-tiny` bare instead.
    if "var(--" in note or "var(--" in name:
        raise SystemExit(
            "the note names a CSS token in callable form (var(--x)). D2R_BUILD.note is a string "
            "literal in bible.html and v1733's token gate cannot tell it from real CSS, so this "
            "would report a token that renders as nothing. Write the token bare: --x")

    # v1613 — REFUSE A VERSION WITHOUT ITS 'v'. Every consumer of these stamps matches `v\d+`:
    # the parity tests, the ship manifest comparison, the badge. Handing this tool a bare "1613"
    # wrote four stamps that all AGREED with each other and none of which any reader could parse —
    # a half-bumped tree by a different route, and worse than a mismatch because the stamps looked
    # internally consistent. It also poisons the next run: `cur` is found by the same `v\d+`
    # pattern, so the tool could no longer find its own previous stamp to replace.
    # v1617 — WHOLE NUMBERS ONLY. Konyo: "we said version go up in whole numbers instead of
    # decimals. so fix that too". Point releases were still being accepted here, so v1616.1 and
    # v1616.2 went out before he caught it. The rule is his and it is easy to keep by hand and easy
    # to forget under momentum, which is exactly the kind of rule that belongs in the tool.
    if not re.match(r"^v\d+$", ver):
        raise SystemExit("version must be a WHOLE number like v1617, not %r — no decimals, and the "
                         "leading 'v' is required (every stamp reader matches it)" % ver)

    # ── v1617 — COMPUTE ALL FOUR, THEN WRITE ALL FOUR ────────────────────────────────────────
    # This used to write each file as it went and raise on the first stamp that did not match. Its
    # own message said "the tree would have been left half-bumped" — but by the time tv_diablo.py
    # failed, bible.html and control_app.py had ALREADY been rewritten, so the sentence described a
    # state the tool had just created rather than one it prevented. (Seen for real stamping v1617
    # over a v1616.1 tree: two files moved, two did not.)
    # Every replacement is now resolved against the ORIGINAL text first; nothing touches disk until
    # all four are known good. The failure mode becomes "nothing happened", which is recoverable.
    repo = repo or REPO
    _preflight(repo)

    today = datetime.date.today().isoformat()
    pending = []          # [(path, new_text)]

    p = os.path.join(repo, "bible.html")
    s = io.open(p, encoding="utf-8").read()
    a = s.index("  window.D2R_BUILD = { id:'")
    b = s.index("\n", a)
    # STRICT ON WHAT IT WRITES, TOLERANT OF WHAT IT FINDS. The guard above refuses to STAMP a
    # decimal, but the tree may still be HOLDING one (v1616.1 shipped before the rule landed), and a
    # tool that cannot read the version it is replacing cannot replace it.
    _m = re.search(r"id:'(v\d+(?:\.\d+)*)'", s[a:b])
    if not _m:
        raise SystemExit("could not find the current D2R_BUILD id in bible.html — nothing written")
    cur = _m.group(1)
    new_line = ("  window.D2R_BUILD = { id:'%s', name:'%s - %s', date:'%s', note:'%s' };"
                % (ver, ver, name, today, note))
    # ⚠ AND PARSE THE ONE LINE THIS TOOL ITSELF GENERATES. `note` is free text that lands inside a
    # single-quoted JS string literal; the guards above refuse an apostrophe and a callable CSS
    # token, which are the two that have bitten, but neither is a parser. This is.
    _new_page = s[:a] + new_line + s[b:]
    # The head is a second copy of this same stamp. Replace the version token in the
    # existing title, and the three metas, before the parse check. A miss refuses
    # here, so nothing is written.
    _new_page = _rewrite_head_stamps(_new_page, ver, today, note)
    _page_problem = _parses_as_page(_new_page)
    if _page_problem:
        raise SystemExit("the bible.html this bump would write does not parse — NOTHING WRITTEN."
                         "\n   %s\n   line: %s" % (_page_problem, new_line[:200]))
    pending.append((p, _new_page))
    # REG-2295 - the name and note must be inert words (stamp_leak.free_text_problem), so gate memory
    # may carry content gates over them. Asked after the older, more specific refusals above so each
    # still names its own reason; still before anything is written.
    for _label, _txt in (("name", name), ("note", note)):
        _inert = free_text_problem(_txt)
        if _inert:  # BUMP-FREE-TEXT-REFUSE
            raise SystemExit("REFUSED to bump %s: the %s carries %s, and gate memory may only carry content "
                             "gates over inert words. Nothing has been written." % (ver, _label, _inert))

    p = os.path.join(repo, "tv", "control_app.py")
    s = io.open(p, encoding="utf-8").read()
    if s.count('"ver": "%s"' % cur) != 1:
        raise SystemExit("control_app.py stamp not found at %s — nothing written" % cur)
    pending.append((p, s.replace('"ver": "%s"' % cur, '"ver": "%s"' % ver)))

    p = os.path.join(repo, "tv", "tv_diablo.py")
    s = io.open(p, encoding="utf-8").read()
    # tolerant read here too — the trailing comment is free text, and the version may be dotted
    s2, n = re.subn(r'VERSION = "v\d+(?:\.\d+)*"   # .*',
                    'VERSION = "%s"   # %s' % (ver, name), s, count=1)
    if n != 1:
        raise SystemExit("tv_diablo.py VERSION line did not match — nothing written")
    pending.append((p, s2))

    p = os.path.join(repo, "tv", "WINDOWS_SHIP.json")
    d = json.load(io.open(p, encoding="utf-8"))
    d["ver"] = ver
    d["note"] = "%s: %s" % (ver, note)
    pending.append((p, json.dumps(d, indent=2, ensure_ascii=False) + "\n"))

    # v3843 - THE VERSION HISTORY. Each ship's bump commit carries its own changelog entry (tv/CHANGELOG.json,
    # newest first): the console's footer history overlay reads it, and test_the_bump_carries_its_changelog_entry
    # holds VERSION == changelog[0].ver. Items are what literally shipped, one per change: explicit, or the note
    # split on ", ". The date is the ship's day in Israel time.
    p = os.path.join(repo, "tv", "CHANGELOG.json")
    log = changelog_with(json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else [], ver, note, items)
    for _it in log[0]["items"]:
        _inert = free_text_problem(_it)
        if _inert:
            raise SystemExit("REFUSED to bump %s: a changelog item carries %s. Nothing has been written." % (ver, _inert))
    pending.append((p, json.dumps(log, indent=2, ensure_ascii=False)))

    for path, text in pending:
        nl = "\n" if path.endswith(".json") else ""
        # ⚠⚠ v2712 — THIS LOOP WAS A TORN-READ GENERATOR, AND HIS CONSOLE IS THE READER.
        # `io.open(path, "w")` TRUNCATES ON OPEN, so between the truncate and the write
        # completing, the file on disk is EMPTY. bible.html is 6 MB and his console EXECS THE
        # WORKING TREE — it re-reads that file per request — so a page load landing in that
        # window parses nothing at all. [[execs-the-working-tree]]
        #
        # MEASURED, not theorised, on a 6,254,422-char copy with a reader polling concurrently:
        #     truncate-then-write   188 reads, 9 TORN (4.8%)   every torn size == 0 bytes
        #     tmp + os.replace      203 reads, 0 TORN (0.0%)
        # The torn reads were not partial parses — they were an EMPTY FILE, which is exactly the
        # symptom he described: "a panel that renders NOTHING and says nothing", unreproducible
        # afterwards because the settled tree is fine.
        #
        # os.replace() is atomic on the same filesystem, so a concurrent reader sees either the
        # whole old file or the whole new one and never a half. The repo already does this in 93
        # places; the four version stamps — the write that runs on EVERY ship — were not among
        # them. [[open-for-write-truncates-first]] [[stale-render]]
        atomic_write(path, text, nl)

    _record_ship_in_tasks(ver, name, note, repo)

    _drop_stale_bytecode([p for p, _t in pending])

    print("%s -> %s  (%s)" % (cur, ver, name))


def changelog_items(note, items=None):
    """What literally shipped, one bullet per change: the explicit list, else the note split on ", "."""
    src = items if items else str(note or "").split(", ")
    return [t.strip() for t in src if str(t or "").strip()]


def changelog_with(log, ver, note, items=None, date=None):
    """`log` (newest first) with `ver`'s entry on top; an entry already there for `ver` is replaced, never doubled."""
    if date is None:
        try:
            from zoneinfo import ZoneInfo
            date = datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d")
        except Exception:
            date = datetime.date.today().isoformat()
    rest = [e for e in (log or []) if isinstance(e, dict) and e.get("ver") != ver]
    return [{"ver": ver, "date": date, "items": changelog_items(note, items)}] + rest


#: v3886 (#107) - how long a Windows replace waits out a reader that holds the target open (40 x 25 ms = 1 s)
_HELD_TRIES, _HELD_WAIT_S = 40, 0.025


def _replace_held(tmp, path, tries=None, wait_s=None, sleep=None):
    """os.replace(tmp, path), waiting out a READER on Windows. -> None (or the last PermissionError, raised)

    windows-latest, test_provenance's concurrent reader: "PermissionError: [WinError 5] Access is denied: store.json.tmp ->
    store.json". Windows refuses to replace a file another handle holds open (Python opens without FILE_SHARE_DELETE), so
    a store read while it is written refused the write - on his PCs, the console's own threads are that reader. The
    replace is retried briefly there; a target still held after the bound raises as before, never a silent skip. Off
    Windows a replace never meets this, and it runs once."""
    tries = _HELD_TRIES if tries is None else tries
    for i in range(max(1, int(tries))):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if os.name != "nt" or i >= int(tries) - 1:
                raise
            (sleep or time.sleep)(_HELD_WAIT_S if wait_s is None else wait_s)


def atomic_write(path, text, nl=""):
    """Write `text` to `path` so a CONCURRENT READER never sees a partial file.

    ⚠⚠ v2712 — THE FOUR-STAMP WRITE WAS A TORN-READ GENERATOR, AND HIS CONSOLE IS THE READER.
    This was `io.open(path, "w", ...).write(text)`, which TRUNCATES ON OPEN. Between the truncate
    and the write completing, the file on disk is EMPTY. bible.html is 6 MB, his console EXECS THE
    WORKING TREE and re-reads it per request, so a page load landing in that window parses nothing
    at all. [[execs-the-working-tree]]

    MEASURED on a 6,254,422-char copy with a reader polling concurrently — not theorised:

        truncate-then-write    188 reads,  9 TORN  (4.8%)   every torn size == 0 bytes
        tmp + os.replace       203 reads,  0 TORN  (0.0%)

    The torn reads were not partial parses. They were an EMPTY FILE, which is precisely the symptom
    he reported: "a panel that renders NOTHING and says nothing", unreproducible afterwards because
    the settled tree is fine. Every attempt to reproduce it on a settled tree was measuring the
    wrong moment. [[feedback-blind-fixture-green-gate]]

    os.replace() is atomic on the same filesystem: a reader sees the whole old file or the whole
    new one, never a half. The repo already did this in 93 places — the one write that runs on
    EVERY ship was not among them. [[open-for-write-truncates-first]] [[stale-render]]

    ⚠ THIS IS PER-FILE, NOT ACROSS THE FOUR. A crash between two stamps still leaves the set
    disagreeing; that is a different defect and this does not fix it. Saying otherwise would be
    the overclaim this repo keeps carving. [[unknown-stays-unknown]]

    ⚠⚠ v2795 — THIS SILENTLY DISABLED THE ENTIRE PRE-PUSH GATE, AND THE PUSH SAID SO IN A HINT
    NOBODY WOULD HAVE READ TWICE. `os.replace` moves the TEMP FILE's inode into place, and the temp
    file is created with the default 0644 — so every executable this function touched came out
    NON-EXECUTABLE. Measured 2026-09-08: `hooks/pre-push` was 100755 at v2793 and 100644 at v2794,
    and git printed

        hint: The 'hooks/pre-push' hook was ignored because it's not set as executable.

    then pushed straight to origin with NO gates at all — no test_control, no render, no smoke, no
    second eye. The atomicity fix and the mode loss are the same line: preserving the CONTENT while
    dropping the PERMISSION is not preserving the file. [[the-unjoined-end]]

    ⚠⚠ v2797 — AND THE v2795 FIX LEFT A WINDOW, FOUND BY A COLD CROSS-FAMILY REVIEW OF THE
    SHIPPED BYTES. v2795 restored the mode by chmod'ing AFTER os.replace. Between those two calls
    the new content is already live under the TEMP FILE's mode, which is born under umask.
    MEASURED, stopping the sequence mid-way:

        target before         0o755
        the temp file's mode  0o644   <- born under umask
        AFTER os.replace      0o644   <- the window
        after os.chmod        0o755

    For `hooks/pre-push` that window IS THE ORIGINAL DEFECT IN MINIATURE: a push starting inside it
    sees a non-executable hook and skips every gate. Not hypothetical here — pushes run in the
    background while other work continues. Reproduced before being believed.

    ⇒ THE MODE GOES ON THE TEMP FILE, BEFORE THE REPLACE, so the final inode appears with its
    content and its permissions in ONE atomic step. The post-replace chmod survives only as a
    fallback for the case where that pre-chmod itself failed.

    ⚠ AND THE TEMP NAME IS UNIQUE NOW. `path + ".tmp"` is deterministic, so two writers on one path
    silently truncate each other's temp file — bump_version writes four stamps and this session
    routinely runs things concurrently. mkstemp in the SAME directory keeps the rename atomic; a
    cross-filesystem rename is not.

    ⚠ NOT CLAIMED: durability. The same review noted there is no fsync of the file or its parent
    directory, so a crash after the replace can leave the entry pointing at unflushed data. That is
    TRUE and is not fixed here — this function's contract is "no torn read", not "survives power
    loss". Saying so beats implying otherwise. [[unknown-stays-unknown]]

    A file that did not exist has no mode to copy and correctly keeps the default.
    """
    try:
        _mode = os.stat(path).st_mode
    except OSError:
        _mode = None
    _dir = os.path.dirname(os.path.abspath(path)) or "."
    _fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=_dir)
    os.close(_fd)
    try:
        with io.open(tmp, "w", encoding="utf-8", newline=nl) as fh:
            fh.write(text)
        # ⛔ BEFORE the replace — the whole point of the v2797 correction.
        # ⚠ AND THE NEW-FILE CASE CHANGED UNDER ME: mkstemp creates 0600, where the old
        #   io.open(path,"w") produced 0666 & ~umask (0644 here). Caught by PRINTING the number
        #   rather than assuming the swap was mode-neutral — a brand-new generated file readable
        #   only by its owner would break anything else on this machine that reads it. So a file
        #   with no previous mode gets the umask default it would always have had.
        try:
            if _mode is not None:
                os.chmod(tmp, _mode & 0o7777)
            else:
                _um = os.umask(0)
                os.umask(_um)
                os.chmod(tmp, 0o666 & ~_um)
        except OSError:
            pass
        _replace_held(tmp, path)
    except BaseException:
        # a failed write must not leave a stray temp beside his files
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    if _mode is not None and (os.stat(path).st_mode & 0o7777) != (_mode & 0o7777):
        try:
            os.chmod(path, _mode & 0o7777)   # fallback: the pre-chmod did not take
        except OSError:
            pass


#: the ship table's header - the newest row goes directly under it
_SHIP_HEAD = "| version | commit | commit subject |\n|---|---|---|\n"


def _ship_table(text):
    """-> the ship table's rows (the contiguous `|` lines under its header), or "" when there is no table."""
    s = text or ""
    i = s.find(_SHIP_HEAD)
    if i < 0:
        return ""
    rows = []
    for ln in s[i + len(_SHIP_HEAD):].splitlines(True):
        if not ln.startswith("|"):
            break
        rows.append(ln)
    return "".join(rows)


def _has_ship_row(text, ver):
    """Does the ship table carry a ROW for this version? -> bool

    ⚠ 2026-09-26 — A VERSION NAMED IN PROSE IS NOT ITS ROW. This check was `ver in s`: any mention anywhere in
    TASKS.md. The #174 task row said "R1 (v3507)" and then "v-B3 (v3509)" - each written just BEFORE its own bump - so
    both bumps read "already recorded by hand" and wrote no ship row; v3507 and v3509 were missing from the table, and
    test_the_newest_ships_appear_in_TASKS_md asked the same loose question and stayed green. Only a table row counts.
    [[a-presence-law-is-not-a-reachability-law]]

    ⚠ 2026-09-30 — AND A ROW IN ANOTHER TABLE IS NOT ITS ROW EITHER. The fix above still matched `| **v3527** |`
    anywhere in the file, and the open queue's IN FLIGHT table keys its rows the same way: "| **v3527** | integrating:
    ..." was written before the bump, so the v3527 bump read it as the ship row and wrote none. Only a row INSIDE the
    ship table counts now."""
    return re.search(r"^\| \*\*%s\*\* \|" % re.escape(ver), _ship_table(text), re.M) is not None


def _record_ship_in_tasks(ver, name, note, repo=None):
    """Write the ship's row into TASKS.md, because remembering to has failed THREE times.

    TASKS.md documents the workflow in its own words: **bump -> record the row here -> commit**,
    and adds that "the gate fails on its own ship if that middle step is skipped - it did, on
    v2670, which is how this line came to exist."

    It then happened again on v2712, v2713 AND v2714, in one session, by the same hand that had
    just read that sentence. `test_tasks_ships_are_recorded` caught it in CI, correctly, three
    ships late.

    ⚠ THE FIX IS NOT TO REMEMBER HARDER. A step that a human (or a model) must remember, in the
    middle of a mechanical sequence the machine is already performing, will be skipped again. The
    bump already edits four files; the list is the fifth surface describing the same event, and
    the tool that moves the stamp is the only thing that reliably knows a ship happened.
    [[the-unjoined-end]] [[copy-drift]]

    Never fatal: a bump that cannot write the list must still bump. A version stamp half-applied
    because a MARKDOWN TABLE could not be edited would be a far worse failure than the one this
    prevents.
    """
    try:
        # ⚠ v3104 — THE ROOT IT WAS GIVEN. With repo= pointed at a fixture tree, a completed
        # bump still wrote a ship row into the REAL TASKS.md. Latent (no test completes a
        # successful bump on a temp root) and cheap to close. [[feedback-fixtures-never-touch-live-data]]
        p = os.path.join(repo or REPO, "TASKS.md")
        s = io.open(p, encoding="utf-8").read()
        if _has_ship_row(s, ver):
            return                              # already recorded by hand; do not duplicate
        # the newest row sits directly under the table header, so anchor on the header itself
        # rather than on whatever version happens to be top today.
        head = _SHIP_HEAD
        if head not in s:
            print("   \u26a0 TASKS.md ship table not found - record %s by hand" % ver)
            return
        row = "| **%s** | `(this commit)` | %s \u2014 %s |\n" % (ver, ver, (note or name or "").strip())
        io.open(p, "w", encoding="utf-8").write(s.replace(head, head + row, 1))
        print("   recorded %s in TASKS.md" % ver)
        # ⚠⚠ AFTER THE WRITE, NOT BEFORE — AND THAT ORDER IS THE WHOLE FIX.
        # v2927 put this block ABOVE the write. `s` was read at the top of this function, the
        # stamper then wrote TASKS.md itself, and the line above wrote STALE `s` straight back over
        # it. MEASURED 2026-09-11: the v2928 bump printed "bound 1 version row(s)" and commit
        # 6442cfe5 still carries `| **v2927** | \u0060(this commit)\u0060 |`. The backfill was
        # real, correct, and clobbered in the same breath — a lost update.
        # ⚠ AND THE LAW WAS HOLLOW. test_bump_version_actually_CALLS_the_stamper asserted the
        # import and the .stamp() call existed, so it proved the tap was PLUMBED and never that
        # water came out. It cites [[plumbing-with-no-tap]] in its own docstring.
        # being written — at bump time the commit genuinely does not exist — but nothing ever came
        # back to replace it, and MEASURED 2026-09-11 that left 249 of 278 rows unable to bind a
        # version to a commit at all. Grok Bot raised it three ticks running (GB-B-403/404/405).
        # The previous version's commit DOES exist by now, so every row but the newest can be
        # bound here. [[the-unjoined-end]] [[plumbing-with-no-tap]]
        try:
            import stamp_versions as _sv
            # ⚠ 2026-09-26 — THE SAME FILE THE ROW WENT TO. A bare stamp() stamped the REAL TASKS.md even when this
            # bump was aimed at a fixture tree (repo=): the v3104 rule, one call further down. [[feedback-fixtures-never-touch-live-data]]
            _r = _sv.stamp(path=p, cwd=(repo or REPO))
            _c = _r["counts"]
            # ⚠⚠ v2936 — A REFUSAL IS A RETURN VALUE, NOT AN EXCEPTION, AND THE `except` BELOW
            # CANNOT SEE IT. v2931 taught stamp() to refuse when `git log` cannot be asked; main()
            # was joined to that and THIS caller was not, so the condition below (all zeros on a
            # refusal) was False and the bump printed only "recorded vNNNN in TASKS.md".
            # MEASURED: with git unreachable, stamp() returned a `why` and this path said nothing.
            # The instrument failure v2931 exists to announce was silent on the one path that runs
            # at every bump — REG-936's own shape, one caller over.
            # [[the-unjoined-end]] [[feedback-silence-is-not-evidence]]
            if _r.get("why"):
                print("   \u26a0 version rows were NOT backfilled: %s" % _r["why"])
            elif _c["bound"] or _c["carried"] or _c["unknown"]:
                print("   bound %d version row(s) to a commit (%d carried, %d UNKNOWN)"
                      % (_c["bound"], _c["carried"], _c["unknown"]))
        except Exception as _e:
            # ⚠ SAY SO. A silent failure here is how the table quietly goes back to 249 unbound
            # rows with everything looking healthy. [[feedback-silence-is-not-evidence]]
            print("   ⚠ version rows were NOT backfilled (%s) — run tv/stamp_versions.py by hand"
                  % type(_e).__name__)
    except Exception as e:
        print("   \u26a0 could not record %s in TASKS.md (%s) - do it by hand" % (ver, str(e)[:80]))


def _drop_stale_bytecode(paths):
    """Delete the cached .pyc for every source this bump just edited.

    ⚠ THIS BUMP'S EDITS ARE INHERENTLY LENGTH-PRESERVING. "v2366" -> "v2367" is the same byte
    count, and Python decides a .pyc is fresh from the source's mtime AND SIZE. Edit twice inside
    one filesystem-timestamp tick and the interpreter keeps running the OLD compiled constants
    against correct source - silently.

    It bit three times on 2026-09-01 alone. The worst was `_app_ver()`, which deliberately reads
    the version out of `status_payload.__code__.co_consts` so it reports what this process is
    RUNNING rather than what is on disk (v2155). With a stale .pyc it answered v2366 while the
    file said v2367, `test_app_ver_equals_ship_version` went red on a correct tree, and a push
    was blocked twice for a defect that did not exist.

    ⚠ AND THE CACHE IS NOT IN __pycache__ ON THIS MAC. `sys.pycache_prefix` relocates it to
    ~/Library/Caches/com.apple.python/<absolute source path>, so anyone deleting __pycache__ and
    concluding "cleared" has cleared nothing. Both locations are removed here.
    [[python-pycache-prefix-mac]]
    """
    import sys as _sys
    removed = []
    for src in paths:
        if not src.endswith(".py"):
            continue
        stem = os.path.basename(src)[:-3]
        cands = []
        prefix = getattr(_sys, "pycache_prefix", None)
        if prefix:
            cands.append(os.path.join(prefix + os.path.dirname(os.path.abspath(src))))
        cands.append(os.path.join(os.path.dirname(os.path.abspath(src)), "__pycache__"))
        for d in cands:
            try:
                if not os.path.isdir(d):
                    continue
                for f in os.listdir(d):
                    if f.startswith(stem + ".") and f.endswith(".pyc"):
                        os.remove(os.path.join(d, f))
                        removed.append(f)
            except Exception:
                pass          # a cache we cannot clear is a warning, never a failed bump
    if removed:
        print("   cleared %d stale .pyc: %s" % (len(removed), ", ".join(sorted(set(removed))[:4])))
    return removed


def _regen_blueprint():
    """BLUEPRINT.md is GENERATED from the code, so a version bump must regenerate it.

    ⚠⚠ MEASURED 2026-09-10: the pre-push gate refused THREE separate pushes in one session with
    "BLUEPRINT.md no longer matches the code" — every time because a version had added or removed a
    gate and the generated map still carried the old count. Each refusal cost a full push cycle:
    the second eye, the blueprint check, the suites, all re-run from the top.

    The gate is RIGHT to refuse and must not regenerate the map itself — the pre-push grades the
    WORKING TREE, so a hook that edits the tree mid-run is grading bytes it just changed. The place
    to do it is HERE, at the bump, where the tree is already being written on purpose.

    ⚠ A FAILURE HERE MUST NEVER FAIL THE BUMP. The four stamps are the ship; the map is a
    convenience. If it cannot regenerate, say so and let the pre-push refuse — that is the gate
    doing its job, not a reason to lose a version stamp.
    """
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        r = subprocess.run([sys.executable, os.path.join(here, "blueprint.py")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if r.returncode == 0:
            print("   regenerated BLUEPRINT.md")
            # ⚠ v3206 — AND THE HEART MAP, for the same reason and by the same rule. His words:
            # "we need it all updated and blueprints updated and heart updated all derived from
            # the console", then "fix this so it is like blueprints too and has enforcemnt".
            # BLUEPRINT.md is the one artefact here that has never drifted, and the reason is
            # that nobody writes it: it is derived, regenerated here, and refused at pre-push when
            # stale. The heart now travels the same road. A failure to regenerate must not cost a
            # version stamp — the pre-push will refuse and a human runs the generator.
            try:
                h = subprocess.run([sys.executable, os.path.join(here, "heart_map.py")],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
                print("   regenerated HEART.md" if h.returncode == 0 else
                      "   ⚠ HEART.md could NOT be regenerated — python3 tv/heart_map.py")
                # v3401 — AND THE RESUME, by the same rule. MEASURED 2026-09-20: RESUME_HERE.md
                # was FOUR DAYS STALE and described a different set of unpushed commits, and
                # nothing noticed because nothing could — it was prose. Its derived half now
                # travels the blueprint road: regenerated here, refused at pre-push when stale.
                # ⚠ Only the block between the markers is written; the narrative outside them is
                # the half a machine cannot measure and is never touched.
                try:
                    rs = subprocess.run([sys.executable, os.path.join(here, "resume_state.py")],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
                    print("   regenerated RESUME_HERE.md" if rs.returncode == 0 else
                          "   ⚠ RESUME_HERE.md could NOT be regenerated — python3 tv/resume_state.py")
                except Exception:
                    print("   ⚠ RESUME_HERE.md could NOT be regenerated — python3 tv/resume_state.py")
            except Exception as exc:
                print("   ⚠ HEART.md regeneration raised %s — run python3 tv/heart_map.py"
                      % type(exc).__name__)
            return True
        print("   ⚠ BLUEPRINT.md could NOT be regenerated (exit %s) — the pre-push will refuse "
              "until it is: python3 tv/blueprint.py" % r.returncode)
    except Exception as exc:
        print("   ⚠ BLUEPRINT.md regeneration raised %s — run python3 tv/blueprint.py by hand"
              % type(exc).__name__)
    return False


if __name__ == "__main__":
    _args = sys.argv[3:]
    _items = None
    if "--items" in _args:
        _i = _args.index("--items")
        _items = [t for t in _args[_i + 1:]]
        _args = _args[:_i]
    bump(sys.argv[1], sys.argv[2], " ".join(_args), items=_items)
    _regen_blueprint()
