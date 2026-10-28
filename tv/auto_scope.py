#!/usr/bin/env python3
"""WHAT EACH AUTOMATIC LANE WILL TOUCH, AND WHAT IT WILL LEAVE ALONE.

★ WHY THIS EXISTS. A different model family was shown the console cold and asked one question with
no hint of the expected answer — "if this app were about to do something on your behalf, could you
tell from these screens what it would do and what it would leave alone?" It answered:

    "CANNOT TELL. The screens show current state and manual controls, but give no indication what
     any automated action would actually touch or skip. No confirmation text or scope is visible."

It is right, and on this machine that matters more than usual: these lanes restart his console,
back up his ledger, and are the same family of code that once deleted reels he wanted.

⚠ A DECLARATION THAT IS ONLY PROSE IS WORSE THAN NONE. "this lane never deletes" written beside a
function that calls os.remove is a lie with a confident face — and it would be believed precisely
because someone bothered to write it down. So every claim here is CHECKED AGAINST THE SOURCE of the
function it describes: a lane that declares it never deletes, and whose code can delete, fails the
gate. The declaration is a promise the tests hold it to. [[unknown-stays-unknown]]

⚠ AND THIS DECIDES NOTHING. It reports scope. It cannot stop a lane, arm one, or change what any of
them do — the same rule health_engine follows, for the same reason: an actor that both decides and
describes will eventually describe what it wishes were true.
"""

#: Each lane: what it MAY touch, what it NEVER touches, and how often it wakes.
#: `forbids` is the load-bearing half — those are the words the source check enforces.
LANES = {
    "tvd-version-drift": {
        "does": "restarts this console onto a newer build already on disk",
        "touches": "this console process, and its own bookkeeping files (see clears)",
        "forbids": ["delete"],
        # REG-2916 (#128) - the restart it drives clears the console's own bookkeeping, named function by function
        "clears": ["stop_agent", "_stop_capture", "_clear_exit_on_purpose", "_capture_health"],
        "never": "your ledger, your reels, your vault — the only files it removes are its own bookkeeping, "
                 "named in CLEARS: the agent and capture pid files, the live eye frame and its own 'closed on "
                 "purpose' marker",
        "when": "when the disk build is newer than the running one",
        "brakes": "refuses while a film is rolling, and refuses into a board that came back a "
                  "different world",
    },
    "tvd-ledger-backup": {
        "does": "copies your ledger aside so a bad write can be undone",
        # 2026-09-27 — and the drop record its watcher keeps (.ledger_drops.json, gitignored):
        # which store fell, from what, and which backup predates it. Said, because a lane that
        # writes a file its declaration does not name is a lane nobody can audit.
        "touches": "its own backup files, and its drop record (.ledger_drops.json)",
        # ⚠ v2410 — THIS DECLARATION CONTRADICTED ITSELF, AND THE AUDITOR HAD BEEN SAYING SO TO
        # NOBODY. `touches: its own backup files` and `forbids: [delete]` cannot both be true of a
        # lane that rotates its own backups — and it does: _ledger_snapshot_once keeps the newest
        # _LEDGER_BACKUP_KEEP and os.remove()s the rest. unverified_reach() has been printing
        # "tvd-ledger-backup · 6 function(s) beyond it NOT audited (something down there can
        # delete)" from a CLI nothing runs.
        #
        # ⚠ THE FIX IS NOT TO DROP "delete" FROM forbids. That would weaken a real guard to silence
        # a TRUE alarm — the worst possible trade. Rotating one's own artefacts is simply not the
        # danger `forbids: delete` exists to prevent, so it gets its own clause that names WHAT and
        # HOW MANY. A permission with a directory and a keep-count is checkable; a blanket
        # exemption is not. The forbid still covers everything else on disk.
        "forbids": ["delete"],
        "rotates": {"dir": "_LEDGER_BACKUP_DIR", "glob": "ledger_*.json",
                    "keep": "_LEDGER_BACKUP_KEEP",
                    "why": "a backup directory that only ever grows fills his disk; the snapshot "
                           "keeps the newest N of its OWN files and removes no others"},
        "never": "the ledger itself — it only ever reads it",
        "when": "on a timer",
        "brakes": "a backup that cannot be written says so rather than pretending it wrote",
    },
    "tvd-eagle-watch": {
        "does": "asks every check how the running system is doing",
        "touches": "nothing — it reports",
        "forbids": ["delete"],
        "never": "any of your data; it has no write path at all",
        "when": "on a ten-minute timer",
        "brakes": "an unmeasurable check reads UNKNOWN, never ok",
    },
    "tvd-runaway-watch": {
        "does": "times its own sleep against the clock and, when it starves while the process "
                "burns CPU, dumps every thread's stack so the spinning frame is NAMED",
        "touches": "its own dump file (runaway_dumps.txt, capped and rolled over) and the fault "
                   "journal row that says a runaway was seen",
        "forbids": ["delete"],
        "never": "your reels, your frames, your ledger or your vault. It reads its own clock and "
                 "the process CPU counter, and the only thing it writes is evidence about itself",
        "when": "on its own short timer, continuously — a watchdog that sleeps through the event "
                "it watches for is not a watchdog",
        "brakes": "the dump file is size-capped with one rollover, because a watchdog that fills "
                  "the disk while reporting a runaway has become the incident",
    },
    "tvd-retro-triage": {
        "does": "surveys one unread reel at a time to learn, for free, which reels are worth "
                "paying to read",
        "touches": "its own triage store — the survey verdicts, one row per reel",
        "forbids": ["delete"],
        "never": "your reels, your frames, your ledger or your vault. It reads footage and "
                 "writes down what it saw; it removes nothing",
        "when": "on a timer, ONE reel per tick — spread out on purpose so it stays "
                "interruptible on the machine you play on, not because it is slow",
        "brakes": "it stands down for five named reasons rather than skipping silently: you are "
                  "playing (D2R is alive), the machine is loaded above its core count, a capture "
                  "is live, a paid sweep is spending, or the disk is below its floor",
    },
    "tvd-retention": {
        "does": "accounts for what old footage COULD be freed",
        "touches": "its own accounting",
        "forbids": [],
        "never": "a reel, unless the prune is armed — and the prune is OFF by his decision",
        "when": "on a timer",
        "brakes": "frame_authority holds any frame whose reel is unsealed, recent, or a witness",
    },
    "tvd-rolling-prune": {
        "does": "would delete old frames while he records — THE ONLY LANE HERE THAT CAN REMOVE HIS "
                "FOOTAGE",
        "touches": "frames inside reels that frame_authority has cleared for deletion",
        "forbids": [],
        "never": "runs at all while the arming flag is off — and it is off, by his decision. Its "
                 "own docstring says 'Prune while he records, indefinitely, exactly as he asked'; "
                 "what stops it is _PRUNE_SAFE_TO_RUN",
        "when": "on a timer, gated by that flag",
        "brakes": "frame_authority refuses any frame whose reel is one of the newest, unsealed, "
                  "named as a witness, or whose state could not be read at all",
    },
    "tvd-stash-watch": {
        "does": "seals a reel once the stash has been off screen long enough",
        "touches": "the seal record for that reel, and the stopped agent's own pid files (see clears)",
        "forbids": ["delete"],
        # REG-2916 (#128) - sealing stops the agent, which clears its own pid files and live eye frame
        "clears": ["stop_agent", "_stop_capture"],
        "never": "the footage itself — sealing marks a reel as read, it does not remove it; the only files it "
                 "removes are the stopped agent's pid files and its live eye frame",
        "when": "after a grace period with no stash on screen",
        "brakes": "only a reel the lane itself declared is sealed this way",
    },
    "tvd-shadow-watch": {
        "does": "looks for the Diablo window and ROLLS A REEL ITSELF when it finds one — the only "
                "lane here that starts a recording without him pressing anything — and closes a "
                "reel IT opened once that reel has run an hour, so an evening is processed in "
                "hour-long pieces instead of one reel at the end",
        "touches": "starts the same capture agent /api/on starts; writes frames into a new reel; "
                   "ends only its OWN shadow reels, through the same stop /api/off uses - which clears the "
                   "stopped agent's pid files; and removes the temporary picture of the launcher it took (see clears)",
        "forbids": ["delete"],
        # REG-2916 (#128) - the stop it shares with /api/off, its rollover's kill, and its own launcher picture
        "clears": ["stop_agent", "_stop_capture", "_force_kill_all_agents", "_launcher_picture"],
        "never": "a SECOND reel — it refuses while an agent is alive or a mini is counting down; "
                 "and it refuses below the 8 GB floor, because a reel the reaper cannot keep alive "
                 "is worse than no reel. It NEVER ends a reel he started himself (ON AIR or MINI), "
                 "whatever its age, nor one whose door or start it cannot read. The only files it removes are the "
                 "stopped agent's pid files, its live eye frame and the launcher picture it took itself",
        "when": "every 20 s, only while the shadow switch is ON; one extra look ~2 s after an "
                "hourly rollover, so the next reel follows the sealed one within seconds",
        "brakes": "the SAME window finder ON AIR and MINI capture through (Quartz on the Mac, the "
                  "Win32 walk on Windows). No window, no reel — so with the game gone a rolled-over "
                  "reel is closed and not reopened.",
    },
    "tvd-vault-autoread": {
        "does": "starts a vault read on footage that is waiting for one",
        "touches": "the vault ledger of what has been SEEN — never what he owns",
        "forbids": ["delete"],
        "never": "his grail; a vault read proposes, and the board is the only thing that writes",
        "when": "when a reel is owed a read",
        "brakes": "the free structural gate refuses a frame that is not a stash screen before any "
                  "paid read happens",
    },
    "tvd-chron-autoread": {
        "does": "starts a chronicle read on footage that is waiting for one",
        "touches": "the sweep's own proposal — a read-only picture until he presses register",
        "forbids": ["delete"],
        "never": "his ledger. Since v2289 the console cannot even call the board directly; it "
                 "leaves a note and he accepts it in the inbox",
        "when": "when a reel is owed a read",
        "brakes": "the gate holds any name without enough witnesses, and nothing is written "
                  "without him",
    },
    "tvd-space-warden": {
        "does": "watches free disk and refuses recording below the floor",
        "touches": "nothing — it refuses, it does not free",
        "forbids": ["delete"],
        "never": "delete anything to make room",
        "when": "on a timer",
        "brakes": "it stops a NEW recording rather than making space",
    },
    # #41 rank 16 (REG-1560)
    "tvd-tooltip-oracle": {
        "does": "runs the shipped item tooltip (the builder's composition, in node over the bible.html on disk) "
                "over their planner's measured tooltip rows and writes down, row by row, whether ours is theirs",
        "touches": "its own receipt file in this console's world, and its lane trace",
        "forbids": ["delete"],
        "never": "bible.html, your ledger, your vault, your reels or your frames - it reads the page and writes "
                 "only its own receipt",
        "when": "a minute after boot, then every 15 minutes; it re-measures only when bible.html moved or the "
                "receipt is six hours old (one node run of about a third of a second per ship)",
        "brakes": "no node on this machine = a receipt saying so, which every reader takes as UNKNOWN - never "
                  "0 rows and never agreement; a receipt the page has moved from is UNKNOWN until re-measured",
    },
    # REG-2463 (#168) - his ruling 2026-10-21, "FOLD + LANE"
    "tvd-orphan-fold": {
        "does": "moves the loose frames of a recording that died before it sealed into a reel of their own, named "
                "by the frames' own timestamps, so the lanes can read them",
        "touches": "loose f_<ms>.jpg frames in this console's hist folder (moved, never copied or rewritten) and "
                   "the new reel's index",
        "forbids": ["delete"],
        "never": "a frame already in a reel, a window an existing reel covers (that would give one recording two "
                 "session ids), or a recording whose newest frame is still inside the gap - it may still be filming",
        "when": "a few minutes after boot, then every half hour",
        "brakes": "asks what is in flight first and moves nothing on a refusal or when nobody can be asked; one fold "
                  "at a time - while the healer's fold runs it moves nothing; what it leaves loose is named",
    },
    # #193 - his "river says unknown now", 2026-10-27
    "tvd-river-warm": {
        "does": "reads this console's own river (the same read the River tab makes) so the Fleet row has a river to "
                "show instead of 'nothing has asked for the river yet'",
        "touches": "nothing on disk - it asks the console's own read-only river route and keeps the answer in memory",
        "forbids": ["delete"],
        "never": "a reel, a frame, a ledger or a stamp - the route it asks is read-only and it never asks it to walk",
        "when": "a minute after a start, then every five minutes only if the last river read is over 15 minutes old",
        "brakes": "never while he plays or the machine is over 80% busy; a read that fails stays a failed read, "
                  "retried on the same cadence, never in a tight loop",
    },
    # #151 - his "a warning sign under the online area", 2026-10-21
    "tvd-disk-sign": {
        "does": "measures how much of the disk his reels, the Grok sessions and the test output hold, for the disk sign "
                "under the ONLINE light (free space itself is read on every status call, not here)",
        "touches": "nothing on disk - it walks three folders and keeps the sizes in memory",
        "forbids": ["delete"],
        "never": "a reel, a frame, a session folder or a ledger - it reads sizes and never moves, writes or removes",
        "when": "two minutes after a start, then every half hour",
        "brakes": "never while he plays or the machine is over 80% busy; each folder walk stops at 20 s and says "
                  "'at least' rather than calling a partial count the total",
    },
}


#: `_fn_source` could not prove it read the function it was asked for. Distinct from None (the
#: function does not exist) because the honest answers differ: absent is a real finding, STALE is
#: "the audit could not be performed", which is UNKNOWN and must never render as a pass.
#: REG-2916 (#128) - WHAT A LANE THAT FORBIDS DELETE MAY STILL CLEAR, BY FUNCTION AND BY THE EXACT TARGET IT REMOVES.
#: undeclared_reach_abilities reported tvd-shadow-watch, tvd-stash-watch and tvd-version-drift as reaching a delete with
#: nothing permitting it. MEASURED in their depth-3 reach: every delete call is the console's own bookkeeping - the agent
#: and capture pid files, the live eye frame, a temporary picture the lane made itself, the 'closed on purpose' marker -
#: never a reel, a frame of his footage, a ledger or the vault. Each entry names the target
#: EXPRESSION as written in that function's delete call; `clears_report` reads the calls out of the code (ast), so a new
#: delete call, a new target, or a new deleting function anywhere in a lane's reach is undeclared until it is named here.
#: The clause is checked against the code, never trusted as prose.
CLEARS = {
    "stop_agent": {"targets": ("PID_PATH", "_eye"),
                   "what": "the agent's pid file (control_agent.pid) and its live eye frame (frames/eye.jpg), "
                           "once the agent is stopped"},
    "_stop_capture": {"targets": ("CAP_PID_PATH",), "what": "the capture agent's pid file, once it is stopped"},
    "_force_kill_all_agents": {"targets": ("PID_PATH",), "what": "the agent's pid file, after every agent was killed"},
    "_capture_health": {"targets": ("CAP_PID_PATH",), "what": "a capture pid file whose process is gone"},
    "_launcher_picture": {"targets": ("path",),
                          "what": "the temporary picture of the launcher it took itself (mkstemp tvd-relook-*.jpg)"},
    "_clear_exit_on_purpose": {"targets": ("path or _exit_on_purpose_path()",),
                               "what": "the console's own 'closed on purpose' marker, once it runs again"},
}


def delete_targets(src):
    """The target of every delete call in one function's source, as written. -> list | None (unparseable)

    os.remove(x) / os.unlink(x) / shutil.rmtree(x, ...) -> "x"; x.unlink() -> "x". Read from the syntax tree, so a
    comment that mentions os.remove is not a delete and a call is never missed for its spelling."""
    import ast
    import textwrap
    try:
        tree = ast.parse(textwrap.dedent(src))
    except Exception:
        return None
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = ast.unparse(n.func)
        if f in ("os.remove", "os.unlink", "shutil.rmtree"):
            out.append(ast.unparse(n.args[0]) if n.args else "")
        elif isinstance(n.func, ast.Attribute) and n.func.attr == "unlink" and not n.args:
            out.append(ast.unparse(n.func.value))
    return out


def clears_report(mod, lane):
    """REG-2916 (#128) - does this lane's `clears` declaration match what its reach actually deletes? -> dict

    {"checked", "permitted", "gaps", "stale", "why"}. A gap is a function in the lane's reach (the same depth-3 walk
    undeclared_reach_abilities reports on) whose delete calls are not ALL named for it - an undeclared function, a target
    CLEARS does not list for it, or a function whose source could not be read (UNKNOWN is a gap, never a pass). `stale`
    names a declared function the reach no longer touches. permitted = a declaration exists and it has no gap."""
    spec = LANES.get(lane) or {}
    declared = list(spec.get("clears") or [])
    fname = LANE_FN.get(lane)
    if not fname:
        return {"checked": False, "permitted": False, "gaps": [], "stale": [], "why": "no function named for this lane"}
    src, walked, why = reachable_source(mod, fname)
    if src is None:
        return {"checked": False, "permitted": False, "gaps": [], "stale": [], "why": why or "no source"}
    gaps, deleting = [], set()
    for fn in walked:
        body = _fn_source(mod, fn)
        if body is None or body is _STALE:
            text = None
            try:
                text = getsource(getattr(mod, fn))
            except Exception:
                text = None
            if text is None:
                if callable(getattr(mod, fn, None)):
                    gaps.append("%s: its source could not be read, so what it deletes is UNKNOWN" % fn)
                continue
            body = text
        if not any(c in body for calls in FORBIDDEN_CALLS.values() for c in calls):
            continue
        targets = delete_targets(body)
        if targets is None:
            gaps.append("%s: its source would not parse, so what it deletes is UNKNOWN" % fn)
            continue
        if not targets:
            continue                        # the words are in prose, not in a call
        deleting.add(fn)
        if fn not in declared:
            gaps.append("%s deletes %s and the lane does not declare it" % (fn, ", ".join(targets)))
            continue
        allowed = set((CLEARS.get(fn) or {}).get("targets") or ())
        for t in targets:
            if t not in allowed:
                gaps.append("%s deletes %s, which CLEARS does not name for it" % (fn, t))
    stale = sorted(set(declared) - deleting)
    return {"checked": True, "permitted": bool(declared) and not gaps, "gaps": gaps, "stale": stale,
            "why": why or ""}


_STALE = "\x00STALE"

import inspect as _inspect_mod
_REAL_GETSOURCE = _inspect_mod.getsource


def _fn_source(mod, name):
    """The source of the function a lane runs. -> str | None | _STALE

    ★ v2438 — THIS RETURNED SOMEBODY ELSE'S FUNCTION FOR ALL ELEVEN LANES, AND TEN OF THEM PASSED.

    `inspect.getsource` slices the file ON DISK at the RUNNING code object's `co_firstlineno`,
    then walks backwards to the nearest `def`. His console runs the build it booted with while the
    tree moves under it, so the moment a version bump adds lines above a lane, every lookup lands
    off by that many lines and returns whatever function the walk-back happens to hit.

    MEASURED 2026-09-02, console on v2436 against a v2437 tree 30 lines longer:

        declared                 actually read
        _ledger_backup_loop  ->  _ledger_snapshot_once   <- the only one that happens to delete
        _prune_loop          ->  live.sort
        _warden_loop         ->  live.sort
        _eagle_watch_loop    ->  _eagle_once
        ... 11 of 11 wrong

    So the eagle reported ONE false MISSING ("tvd-ledger-backup promises it never deletes, and
    _ledger_backup_loop itself calls os.remove(") and — far worse — TEN SILENT PASSES about
    functions nobody declared. `check_declarations`' OK line, "no lane's own body contradicts its
    promise", was a statement about ten unrelated bodies. **`tvd-rolling-prune` is the only lane
    that can remove his footage and it was being audited against `live.sort`.**

    ⚠ THIS REPO ALREADY CLOSED THIS EXACT DEFECT AND NEVER SWEPT IT. `control_app._app_ver()`
    carries the same paragraph and was fixed at v2155 (#175) by reading `co_consts` instead of
    slicing the file. `co_firstlineno` appears nowhere in this module; the sibling sat here for
    283 versions. [[feedback-generalize-fixes]] [[sweep-dont-ask]]

    THE FIX IS TO VERIFY THE INSTRUMENT GOT WHAT IT ASKED FOR — not to follow more hops. A
    transitive walk was already measured and rejected next door (`undeclared_reach_abilities`:
    reach 6, 23, 34 and **71**, "in a module this size nearly everything reaches everything"), and
    trading one false red for four is not an improvement.

    ⚠ AND IT MUST BE UNKNOWN, NOT A SKIP. "The file on disk no longer matches the running process"
    is a true and useful statement; silently passing the lane would convert a visible false red
    into an invisible false green, which is the direction that gets somebody's footage deleted.
    """
    import inspect
    import re as _re
    fn = getattr(mod, name, None)
    if fn is None:
        return None
    try:
        src = inspect.getsource(fn)
    except Exception:
        return None
    # the whole guard: does the text we were handed actually START with the def we asked for?
    if not _re.match(r"[ \t]*(async[ \t]+)?def[ \t]+%s[ \t]*\(" % _re.escape(name), src):
        return _STALE
    return src


def file_def(path, name):
    """The def named `name` as it sits on disk. -> str | None | _STALE

    ★ CF-15 — `inspect.getsource` is the WRONG instrument for a source-reading guard that
    runs inside a long suite. It slices the file at the RUNNING code object's
    `co_firstlineno` (a fact about the import, not the file). Measured in the full
    `test_control` run: `drift_may_relaunch` was handed `_drift_once`, and
    `_theatre_sessions` was handed `_load_journal_cached`. Isolation the same minute
    was green. The product was fine; the instrument was reading a neighbour.

    AST-from-disk cannot land on a neighbour unless two defs share a name — and two
    defs sharing a name is itself STALE (ambiguous), not a pass. None means the name
    is absent. Same three-way as `_fn_source`.
    """
    import ast
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except Exception:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return _STALE
    hits = [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if not hits:
        return None
    if len(hits) > 1:
        return _STALE
    n = hits[0]
    start = n.lineno - 1
    end = getattr(n, "end_lineno", None)
    if end is None:
        return _STALE
    lines = src.splitlines(True)
    return "".join(lines[start:end])


def getsource(obj):
    """inspect.getsource, refusing a neighbour's body.

    CF-15, measured on the blocked v2453 push: 39 failures / 4 errors, 480s. Isolation
    of the same tests was green. inspect.getsource had sliced the file at a stale
    co_firstlineno and handed `_drift_once` for `drift_may_relaunch`, `fleet_presence`
    for `fleet_compare`, `_exec_soon` for `board_window`.

    If the inspect slice STARTS with the def we asked for, keep it (decorators live
    on that slice). If it does not, the unique def on disk is the source. STALE /
    absent / a class or module falls back to inspect — we do not invent a body.

    ⚠ CALL THE SAVED REAL inspect.getsource. test_control patches inspect.getsource
    to THIS function; using the module attribute would recurse until the stack dies,
    and the 39 reds would become a hang that looks like a hung suite.
    """
    import re as _re
    try:
        src = _REAL_GETSOURCE(obj)
    except Exception:
        src = None
    name = getattr(obj, "__name__", None)
    if not name or str(name).startswith("<"):
        if src is None:
            raise TypeError("could not get source")
        return src
    short = str(name).rsplit(".", 1)[-1]
    if src and _re.match(r"[ \t]*(async[ \t]+)?def[ \t]+%s[ \t]*\(" % _re.escape(short), src):
        return src
    try:
        path = _inspect_mod.getfile(obj)
    except TypeError:
        if src is None:
            raise
        return src
    disk = file_def(path, short)
    if disk not in (None, _STALE):
        return disk
    if src is None:
        raise OSError("could not get source for %s" % short)
    return src


def reachable_source(mod, name, depth=3):
    """The source of `name` AND of everything it calls, to `depth`. -> (text, [names], why)

    ⚠ THE ONE-FRAME READ COULD NOT FAIL, AND I ONLY FOUND THAT BY CALIBRATING IT. Making the
    retention lane promise "never deletes" produced NO break — because _retention_loop does not
    delete inline, it CALLS something that does. A promise checked one frame deep is a promise
    about a function's own text, not about what running it can do, and it would have shipped as a
    confident green.

    So the check follows the call graph, using co_names rather than a text scan: reading the
    IDENTIFIERS a function actually references is the instrument this repo already learned to
    prefer over grepping its own prose. Bounded by depth and a visited set, and it REPORTS what it
    could not follow — a name it cannot resolve is a hole in the promise, not a pass.
    [[source-reading-guard]] [[feedback-suspect-the-instrument]]
    """
    import inspect
    seen, out, unresolved = set(), [], []

    def walk(fname, d):
        if d < 0 or fname in seen:
            return
        seen.add(fname)
        fn = getattr(mod, fname, None)
        if fn is None or not callable(fn):
            return
        try:
            out.append(inspect.getsource(fn))
        except Exception:
            unresolved.append(fname)
            return
        code = getattr(fn, "__code__", None)
        if code is None:
            return
        for n in code.co_names:
            # only follow names this module actually owns; a stdlib call is not ours to audit
            nxt = getattr(mod, n, None)
            if callable(nxt) and getattr(nxt, "__module__", None) == getattr(mod, "__name__", None):
                walk(n, d - 1)

    walk(name, depth)
    if not out:
        return None, sorted(seen), "no source could be read for %s" % name
    return "\n".join(out), sorted(seen), ("could not read: %s" % ", ".join(unresolved)
                                          if unresolved else "")


#: the loop function behind each lane name, so a claim can be checked against real code
LANE_FN = {
    "tvd-version-drift": "_drift_loop",
    "tvd-ledger-backup": "_ledger_backup_loop",
    "tvd-eagle-watch": "_eagle_watch_loop",
    "tvd-retention": "_retention_loop",
    "tvd-space-warden": "_warden_loop",
    "tvd-rolling-prune": "_prune_loop",
    "tvd-stash-watch": "_stash_watch_loop",
    "tvd-vault-autoread": "_vault_autoread_loop",
    "tvd-shadow-watch": "_shadow_watch_loop",
    "tvd-chron-autoread": "_chron_autoread_loop",
    "tvd-retro-triage": "_retro_triage_loop",
    "tvd-runaway-watch": "_runaway_watch_loop",
    "tvd-tooltip-oracle": "_tooltip_oracle_loop",
    "tvd-orphan-fold": "_orphan_fold_loop",
    "tvd-river-warm": "_river_warm_loop",
    "tvd-disk-sign": "_disk_sign_loop",
}

#: what a forbidden word means in code. Deliberately broad: a false alarm costs a comment, a missed
#: one costs his data.
FORBIDDEN_CALLS = {
    "delete": ("os.remove(", "os.unlink(", "shutil.rmtree(", ".unlink()"),
}


def check_declarations(mod):
    """Every lane's promise, checked against the source of the function it names. -> list of breaks.

    A lane that declares it never deletes, and whose loop body can delete, is reported. So is a
    lane with no declaration at all, and a declaration naming a function that does not exist —
    because a promise about code nobody can find is not a promise.
    """
    breaks = []
    for lane, spec in sorted(LANES.items()):
        fname = LANE_FN.get(lane)
        if not fname:
            breaks.append("%s: declared but no function is named for it, so nothing can be "
                          "checked" % lane)
            continue
        # ⚠ THE DIRECT BODY IS WHAT THIS CAN PROVE. A transitive walk found _drift_loop "reaches
        # os.remove" after 59 functions — in a module this size nearly everything reaches
        # everything, so that is not evidence of anything and reporting it as a broken promise
        # would be a false alarm. A guard that cries wolf is how a real one stops being read.
        # So: the lane's OWN body is CHECKED, the wider reach is MEASURED AND REPORTED as
        # unverified, and the two are never mixed. [[unknown-stays-unknown]]
        direct = _fn_source(mod, fname)
        if direct is None:
            breaks.append("%s: names %s, which does not exist — the declaration describes code "
                          "nobody can find" % (lane, fname))
            continue
        if direct is _STALE:
            # v2438 — the audit COULD NOT BE PERFORMED. Say that, rather than passing the lane on
            # evidence about a function nobody declared. This is the ten-silent-passes case, and
            # the fix is only worth anything because it refuses in the QUIET direction too.
            breaks.append("%s: the file on disk no longer matches the running process, so %s "
                          "could not be read — this lane is UNAUDITED, not clean. Relaunch the "
                          "console to re-measure." % (lane, fname))
            continue
        for word in spec.get("forbids") or []:
            for call in FORBIDDEN_CALLS.get(word, ()):
                if call in direct:
                    breaks.append("%s promises it never %ss, and %s itself calls %s"
                                  % (lane, word, fname, call))
    return breaks


def _rotates_is_wellformed(mod, rot):
    """Is this a real, scoped rotation permission — or a flag? -> bool

    ⚠ PRODUCTION USED TO ASK `bool(spec.get("rotates"))`. A cold review put it exactly: the clause
    was "documentation that a future edit can quietly widen", and the schema tests policed the
    dict's shape while the code that GRANTS the permission never looked at a single field. Copy the
    key onto another lane, or empty its contents, and every test stays green while the permission
    spreads.

    So the grant now requires what the clause claims: a directory and a keep-count that CONTROL_APP
    ACTUALLY DEFINES, a glob, and a stated reason. A permission naming something nobody can find is
    the same defect check_declarations already refuses for LANE_FN — "a promise about code nobody
    can find is not a promise" — applied to the permission rather than the prohibition.

    ⚠ AND A KEEP OF ZERO IS NOT ROTATION. It is deletion under a friendlier word, so it does not
    grant. [[the-unjoined-end]] [[unknown-stays-unknown]]
    """
    if not isinstance(rot, dict):
        return False
    if not str(rot.get("glob") or "").strip() or not str(rot.get("why") or "").strip():
        return False
    d, keep = rot.get("dir"), rot.get("keep")
    if not d or not keep or not hasattr(mod, d) or not hasattr(mod, keep):
        return False
    val = getattr(mod, keep, None)
    return isinstance(val, int) and not isinstance(val, bool) and val > 0


def undeclared_reach_abilities(mod):
    """Lanes that FORBID an ability and can nonetheless reach one, with no clause permitting it.

    -> list of dicts {lane, ability, functions, permitted}

    ⚠ THIS IS A NARROWER QUESTION THAN unverified_reach AND THAT IS THE WHOLE POINT. That function
    reports raw reachability and warns, correctly, that it must never be rendered as a verdict — in
    a module this size everything reaches everything. This one reports the INTERSECTION of what a
    lane PROMISED NOT TO DO with what its reach can actually do, which is a different and much
    smaller set. Measured at the shipped depth on 2026-09-01: exactly ONE lane of eleven.

    ⚠⚠ AND MY FIRST DRAFT OF THIS DOCSTRING CLAIMED "exactly ONE lane of eleven", WHICH IS FALSE.
    I read it off a GREPPED EXCERPT of the CLI output that happened to show one row, and wrote the
    number down as if I had counted. Measured properly, on the same tree, the same minute:

        tvd-ledger-backup   delete   reach= 6   permitted=True   (rotates its own backups)
        tvd-shadow-watch    delete   reach=23   permitted=False
        tvd-stash-watch     delete   reach=34   permitted=False
        tvd-version-drift   delete   reach=71   permitted=False

    FOUR, and one of them reaches seventy-one functions. So the original author's noise argument
    STANDS and my "one row is a signal" did not survive contact with the measurement: at reach=71
    this is exactly the everything-reaches-everything case that would make a gate cry wolf.

    THEREFORE THIS REPORTS AND DOES NOT REFUSE. It is strictly more informative than
    unverified_reach — it names WHICH forbidden ability is reachable and whether a clause permits
    it — and strictly less authoritative than the direct-body check. The one row that is actually
    actionable (ledger-backup, reach 6, now carrying an explicit `rotates` clause) was found by
    reading it, not by a gate failing.

    ⚠ DO NOT PROMOTE THIS TO A FAILING GATE ON THE STRENGTH OF THE LEDGER-BACKUP CASE. Three of
    the four rows are almost certainly reach-noise, and a gate that fails on all four teaches him
    to skip the row — the exact defect CF-10 records three instances of. Narrowing it honestly
    (a shorter depth, or following only the call path that actually performs the ability) is real
    work, not a parameter tweak. [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]

    ⚠ A lane may legitimately do a forbidden-sounding thing to its OWN artefacts. That is declared
    with a `rotates` clause naming the directory, the glob and the keep-count — checkable, unlike a
    blanket exemption — and such a lane is reported as PERMITTED rather than as a break.

    REG-2916 (#128) - and a lane whose reach clears the console's own bookkeeping (pid files, a temporary picture it
    made, its own marker) declares it with a `clears` clause: the functions, and in CLEARS the exact target each one
    removes. clears_report reads every delete call in the reach out of the code and permits the row only when each one
    is named - a new delete, a new target or a new deleting function anywhere in the reach makes it a break again.
    """
    out = []
    for lane in sorted(LANES):
        spec = LANES[lane]
        forbids = spec.get("forbids") or []
        if not forbids:
            continue
        u = unverified_reach(mod, lane)
        if not u.get("checked"):
            continue                       # UNKNOWN is reported by unverified_reach, not here
        for ability in sorted(set(u.get("reachesAbilities") or [])):
            if ability not in forbids:
                continue
            out.append({"lane": lane, "ability": ability,
                        "functions": u.get("functions"),
                        "permitted": (ability == "delete"
                                      and (_rotates_is_wellformed(mod, spec.get("rotates"))
                                           # REG-2916 - or every delete in its reach is one its clears clause names
                                           or (bool(spec.get("clears")) and clears_report(mod, lane)["permitted"]))),
                        "why": ((spec.get("rotates") or {}).get("why")
                                or ("clears only its own bookkeeping: " + "; ".join(
                                    (CLEARS.get(f) or {}).get("what", f) for f in spec.get("clears") or [])
                                    if spec.get("clears") else None))})
    return out


def unverified_reach(mod, lane):
    """How far this lane's calls go, and whether anything down there can delete. -> dict

    ⚠ THIS IS NOT A VERDICT AND MUST NEVER BE RENDERED AS ONE. It is the honest statement of what
    the direct check does NOT cover: "this lane's body does not delete, and it calls into N
    functions that were not audited". Presenting reachability as proof of danger would be as wrong
    as presenting its absence as proof of safety — in a module this size a walk of 59 functions
    touches most of the file, and everything reaches everything.
    """
    fname = LANE_FN.get(lane)
    if not fname:
        return {"checked": False, "why": "no function named for this lane"}
    src, walked, why = reachable_source(mod, fname)
    if src is None:
        return {"checked": False, "why": why or "no source"}
    can = sorted({w for w, calls in FORBIDDEN_CALLS.items() if any(c in src for c in calls)})
    return {"checked": True, "functions": len(walked), "reachesAbilities": can,
            "why": why or "",
            "note": "reachability, not behaviour — the direct body is what was verified"}


def say(lane):
    """One line he can read before a lane acts. -> str"""
    s = LANES.get(lane)
    if not s:
        return "%s has no declared scope — what it would touch is UNKNOWN" % lane
    return "%s · touches %s · never %s · %s" % (s["does"], s["touches"], s["never"], s["brakes"])


def report():
    """Every lane, for the console. -> dict"""
    return {"lanes": {k: dict(v, say=say(k)) for k, v in LANES.items()}, "count": len(LANES)}


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    import control_app as _ca
    bad = check_declarations(_ca)
    print("\n🤖 WHAT RUNS WITHOUT YOU, AND WHAT IT TOUCHES\n")
    for lane in sorted(LANES):
        s = LANES[lane]
        print("  %-20s %s" % (lane, s["does"]))
        print("  %-20s   touches: %s" % ("", s["touches"]))
        print("  %-20s   NEVER:   %s" % ("", s["never"]))
        print("  %-20s   brakes:  %s" % ("", s["brakes"]))
        print()
    print("  ── what was PROVEN, and what was not ──")
    for lane in sorted(LANES):
        u = unverified_reach(_ca, lane)
        if u.get("checked"):
            print("  %-20s body verified · %d function(s) beyond it NOT audited%s"
                  % (lane, u["functions"],
                     (" (something down there can %s)" % "/".join(u["reachesAbilities"]))
                     if u["reachesAbilities"] else ""))
        else:
            print("  %-20s ⚪ could not be checked — %s" % (lane, u.get("why")))
    print()
    if bad:
        print("🔴 %d declaration(s) the CODE contradicts:" % len(bad))
        for b in bad:
            print("     %s" % b)
        raise SystemExit(1)
    print("🟢 no lane's own body contradicts its promise.")
    print("⚠ that is a check of each lane's OWN code, not of everything it calls — the line above")
    print("  says how much was left unaudited, because a promise nobody measured is not a promise.")
