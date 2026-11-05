#!/usr/bin/env python3
"""LANE HEALTH — every extraction lane says when it last did work, and a stalled one says so ITSELF.

Konyo, 2026-08-29, after asking why nothing had been extracted "for days" and having to be told:
"eagle eye watchdog.. corroborator all need to be coded accordingly so its all working and
communicating.. we need this ready for traffic and optimized and self looped like the rest of the
system. intelligent architecture code"

⚠ THE FAILURE THIS EXISTS FOR, MEASURED THE DAY IT WAS WRITTEN:

    chronicle_swept.json    36 sessions   newest seal   49.2 h ago    working
    vault_swept.json         8 sessions   newest seal  136.7 h ago    STALLED 5.7 DAYS
    sessions the chronicle lane swept that the vault lane never sealed: 36

frame_authority reads the VAULT seal, so those 36 sessions' frames were all held as "not sealed"
and nothing was prunable. Nothing on the console said the vault lane had stopped. The auto-sweep
watchdog (_chron_autoread_watch, v2139) speaks only when its MESSAGE CHANGES — the right fix for a
loop that logged 1,700 lines a day, and the exact wrong shape for a lane that has been answering
the same thing for five days. Silence had become the report. [[feedback-silence-is-not-evidence]]

THREE THINGS, and they are deliberately separate:
  · FRESHNESS  — when did this lane last produce work, and is that longer than it should be
  · REACH      — how much of the corpus has it covered
  · DIVERGENCE — where two lanes disagree about the SAME session, which is the defect above and
                 which neither lane can see on its own. This is the corroborator's job.

⚠ IT DECIDES NOTHING AND WRITES NOTHING. Same shape as prune_shadow and slot_identity: it reads,
it explains, and an unreadable store makes it answer UNKNOWN rather than healthy. A watchdog that
cannot tell "quiet" from "dead" is the thing being replaced here.
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

#: name -> (store file, human description, stall threshold in HOURS)
# ⚠ THE THRESHOLDS ARE A JUDGEMENT AND ARE LABELLED AS ONE. They are not tuned against anything;
# they are "longer than this and a person would want to know", which is the only honest basis until
# there is a distribution to fit. They are here, named, rather than buried as literals.
LANES = {
    "chronicle": ("chronicle_swept.json", "reads item NAMES off reels into his Chronicle", 48.0),
    "vault":     ("vault_swept.json",     "seals a reel as fully extracted — the ONLY seal the "
                                          "frame deleter reads", 48.0),
    # ⚠ v2304 — SHADOW-WATCH DELIBERATELY IS NOT A LANE HERE. I added it and it turned the whole
    # lanes check UNKNOWN ("a lane's store could not be read"), because everything in this dict is
    # a SWEEP LEDGER keyed by session id with a timestamp per row, and the watcher writes a single
    # flat record of its last look. Forcing a watcher into a ledger's schema broke the reading for
    # the two lanes that were fine. Its health lives in health_engine.check_shadow_watch and its
    # corroboration in corroborate.py, which is where two independent measurements belong.
}

#: lanes that should cover the same sessions. A session in the first and not the second is the
#: divergence that hid a five-day stall.
CORROBORATE = [("chronicle", "vault")]


def _sid(key):
    """ONE spelling for a session id. -> str

    ★ v2302 — THE TWO LANE STORES SPEAK DIFFERENT DIALECTS, AND THE CORROBORATOR NEVER KNEW.
    MEASURED on his tree 2026-08-30:

        chronicle_swept.json keys look like  'reel_s_1785711283831_49223'   (reel_ prefix)
        vault_swept.json     keys look like  's_1787244002054_15361'        (no prefix)

    divergence() computed set(a) - set(b) on those raw keys, so it compared the two lanes in two
    languages. It reported "36 session(s) the chronicle lane covered that vault never did"; the
    truth, normalised against the 28 reels actually on disk, is 20 — with 8 covered by BOTH and
    read as diverged purely because of the prefix.

    ⚠ AND IT COULD NEVER HAVE SAID "ALIGNED". Every chronicle key carries a prefix no vault key
    ever has, so the difference is non-empty BY CONSTRUCTION on any tree, forever. A corroborator
    that cannot report agreement has stopped carrying information — the same defect as a gate that
    is always green, wearing the other colour. Its own docstring says it exists because "no one
    asked them the same question"; it was asking in two dialects.

    Normalised HERE, at the single place both stores are read, and never at the call sites — the
    next store to arrive would otherwise recreate this. [[copy-drift]] [[the-unjoined-end]]
    """
    k = str(key)
    return k[5:] if k.startswith("reel_") else k


def _load(name):
    """-> (dict|None, why). None means UNREADABLE, which is never healthy.

    Keys come back NORMALISED through _sid, so every caller compares like with like."""
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return None, "%s does not exist" % name
    try:
        with io.open(p, encoding="utf-8") as fh:
            blob = json.load(fh)
    except Exception as e:
        return None, "%s could not be read: %s" % (name, e)
    if not isinstance(blob, dict):
        return None, "%s is not a mapping of sessions" % name
    # v2302 — one dialect from here down. Collisions cannot occur: two keys only normalise to the
    # same id if they name the same session, which is exactly what we want them to do.
    return {_sid(k): v for k, v in blob.items()}, ""


def _newest_ts(blob):
    """Newest seal timestamp in ms, or None if no row carries one."""
    best = None
    for v in (blob or {}).values():
        if not isinstance(v, dict):
            continue
        ts = v.get("ts")
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            continue
        if ts and (best is None or ts > best):
            best = ts
    return best


def lane(name, now_ms=None, owed=None, actionable=None, blocked_why=None):
    """One lane's health. -> dict

    ★ v2301 — A LANE WITH NOTHING TO DO IS NOT A LANE THAT STOPPED, and this could not tell them
    apart. It measured ONE thing — how long since the lane last did work — against a stall
    threshold, so a lane that has swept everything and is correctly quiet reports the same
    "STOPPED" as one that is broken.

    MEASURED on his console 2026-08-30, two checks of the same doctor contradicting each other in
    the same breath:
        reel extract      ok       all 28 reel(s) have been read
        extraction lanes  missing  chronicle: last did work 63.5 h ago -- this lane has STOPPED
    Everything was read. There was no work. The lane was idle, and the panel called it stopped —
    which is the kind of red herring that sends him hunting a fault that does not exist, minutes
    before a recording session. [[feedback-contradiction-is-the-finding]]

    `owed` is how many units of work were actually WAITING. IDLE is claimed only on POSITIVE
    evidence that the answer is zero: owed=None means nobody counted, and an uncounted lane stays
    STALLED, because "nothing was owed" and "nobody looked" must never reach the same box.
    [[unknown-stays-unknown]]
    """
    if name not in LANES:
        return {"lane": name, "state": "unknown", "why": "no lane called %r" % name}
    store, what, stall_h = LANES[name]
    blob, why = _load(store)
    if blob is None:
        return {"lane": name, "state": "unknown", "sessions": None, "ageHours": None,
                "why": "%s — an unreadable store is UNKNOWN, never healthy" % why}
    now = float(now_ms if now_ms is not None else time.time() * 1000.0)
    ts = _newest_ts(blob)
    if ts is None:
        return {"lane": name, "state": "unknown", "sessions": len(blob), "ageHours": None,
                "why": ("%d session(s) sealed but not one row carries a timestamp, so HOW LONG AGO "
                        "is unanswerable" % len(blob))}
    age = (now - ts) / 3600000.0
    over = age > stall_h
    idle = bool(over and isinstance(owed, int) and owed == 0)
    # ⚠⚠ v3265 — BLOCKED IS NOT STOPPED. A lane that owes work and can act on NONE of it is
    # waiting on something nobody has supplied, not failing to run. Measured: chronicle owed 4,
    # sweepable 0, because none of those reels has a chosen Chronicle focus. "STOPPED" sent me
    # looking for a dead thread that was alive, switched on, and entirely correct.
    # ⚠ `actionable is None` means nobody counted, so the verdict is left exactly as it was.
    blocked = bool(over and not idle and isinstance(owed, int) and owed > 0
                   and isinstance(actionable, int) and actionable == 0)
    stalled = bool(over and not idle and not blocked)
    if blocked and blocked_why:
        # REG-3200 - THE LANE'S OWN REASONS, NOT THE CHRONICLE'S. The tail below is the chronicle's measured story
        # (no chosen Chronicle focus); a lane that can say what each owed unit waits on says that instead.
        tail = (" — past the %.0f h mark, BUT it owes %d read(s) and can start NONE of them now, so this lane is "
                "BLOCKED, not stopped: %s" % (stall_h, owed, blocked_why))
    elif blocked:
        tail = (" — past the %.0f h mark, BUT it owes %d read(s) and can act on NONE of them, so "
                "this lane is BLOCKED, not stopped: it is waiting on something nobody has "
                "supplied. Measured 2026-09-17: the four reels it owes have no chosen Chronicle "
                "focus, and `chronicle_sweep_now` answers 'nothing waiting: every reel with a "
                "chosen Chronicle focus has been swept'. A dead thread and a lane with nothing it "
                "may touch are different faults and only one of them is fixed by restarting "
                "anything." % (stall_h, owed))
    elif idle:
        tail = (" — but %s owed a read, so this lane is IDLE, not stopped: it has swept everything "
                "there is" % ("nothing" if owed == 0 else "%d" % owed))
    elif stalled:
        tail = (" — past the %.0f h mark, so this lane has STOPPED and nothing else was going "
                "to say so%s" % (stall_h,
                                 "" if owed is not None else
                                 " (and nobody counted what was owed, so IDLE cannot be ruled in)"))
    else:
        # ★ v2439 — A BARE AGE IS NOT A VERDICT, AND IT READ AS ONE. Cross-family, cold, on
        # v2437's panel text: "'last did work 21.9 h ago' — a precise idle time with no verdict,
        # so it can be read as a problem it has not earned", and among what a reader needs and
        # cannot get: "whether 21.9 h is late or normal". The threshold that decides it was
        # nowhere on the screen. A number he could act on, published without the thing that gives
        # it meaning. [[unknown-stays-unknown]] [[stale-reading]]
        tail = " — well inside the %.0f h mark, so this lane is FRESH" % stall_h
    return {
        "lane": name,
        "state": ("idle" if idle else ("blocked" if blocked else ("stalled" if stalled else "fresh"))),
        # ⚠ v3265 — published beside the state so a caller can act on the GAP rather than re-derive
        # it. owed - actionable is the number of units this lane is holding but may not touch.
        "actionable": actionable,
        "sessions": len(blob), "ageHours": round(age, 1), "stallAfterHours": stall_h,
        "what": what, "owed": owed,
        "why": "%s: %d session(s), last did work %.1f h ago%s" % (name, len(blob), age, tail),
    }


def _reels_on_disk():
    """Session ids that still have FOOTAGE. -> (set|None, why)

    None means the store could not be READ, which is UNKNOWN and must never be read as "no
    reels" — an empty set would silently turn every divergence into "aligned", i.e. a green
    corroborator produced by not looking. [[unknown-stays-unknown]]

    ⚠ Honours TV_HIST, because a fixture that repoints the ledgers and not the footage would
    compare his real reels against a test's sessions. Same resolution rule as
    reel_retention.plan, and a reel is a `reel_*` DIRECTORY there — the loose .jpg frames beside
    them are not reels. Keys come back through _sid so all three dialects compare like with like.
    """
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
    try:
        return {_sid(d) for d in os.listdir(hist) if d.startswith("reel_")}, ""
    except OSError as e:
        return None, "cannot read %s: %s" % (hist, e)


def _tally(sessions, held):
    """'4 test-fixture, 5 recent' — the reasons, counted, in one phrase."""
    counts = {}
    for s in sessions:
        counts[held.get(s) or "unlabelled"] = counts.get(held.get(s) or "unlabelled", 0) + 1
    return ", ".join("%d %s" % (n, t) for t, n in
                     sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def held_by_design(sessions):
    """Why is each of these reels being kept? -> {sid: tag} or None if nobody could say.

    ⚠⚠ v3266 — THE DIVERGENCE WAS DESCRIBING A CORRECT SYSTEM AS A BACKLOG. It said, on his
    console, in the sentence the heart leads with:

        9 reel(s) still on disk need a vault sweep — chronicle read them, vault never sealed
        them, and vault's seal is the one the frame deleter reads, so they stay held.
        Sweep vault to free them.

    MEASURED 2026-09-17, every one of the nine, against `reel_retention.plan()`:

        4  test-fixture   the TEST SUITE opens this reel by name
        5  recent         one of the 8 most recent, kept so a re-sweep always has material

    And against the vault lane's own doctrine (`_vault_owed_reels`), which owes **3** reels,
    NONE of them in the nine: the vault owes not one of the reels the panel told him to sweep.
    The prescription could not be followed, and following it is exactly the 2026-09-01 incident
    the retention rules were written to stop — a rewrite that would have queued 26 reels, 10 of
    them explicitly held, at a measured cost of up to 97 paid reads.

    So the count was right and the WORD OVER IT stopped being true. [[label-outlived-referent]]

    ⚠ None means nobody could ask, which is UNKNOWN and keeps the old sentence. An empty dict
    means the question was asked and nothing is held — a different fact.
    """
    try:
        import reel_retention as _RR
        _p = _RR.plan()
    except Exception:
        return None
    if not _p.get("ok"):
        return None
    out = {}
    for _rec in list(_p.get("candidates") or []) + list(_p.get("kept") or []):
        _r = str((_rec or {}).get("reel") or "")
        if _r:
            out[_sid(_r)] = (_rec or {}).get("tag")
    return {s: out[s] for s in sessions if s in out}


def owed_sessions(lane_name):
    """Which sessions does this lane ACTUALLY owe a read? -> set or None (uncounted).

    ⚠ This is the lane's own doctrine, not a ledger difference. The two disagree on purpose:
    a ledger difference says "b never sealed this", the doctrine says "and b is right not to".
    """
    try:
        import control_app as _ca
    except Exception:
        return None
    if lane_name != "vault":
        return None
    try:
        rows = _ca._vault_owed_reels()
    except Exception:
        return None
    if rows is None:
        return None
    return {_sid(os.path.basename(str(r).rstrip("/"))) for r in rows}


def divergence(a, b, owed_by=None, held=None):
    """Sessions lane A covered that lane B never did. -> dict

    Neither lane can see this on its own, which is exactly why it hid a five-day stall: the
    chronicle lane was correct that it had swept, and the vault lane was correct that it had not,
    and no one asked them the same question.
    """
    sa, wa = _load(LANES.get(a, ("", "", 0))[0])
    sb, wb = _load(LANES.get(b, ("", "", 0))[0])
    if sa is None or sb is None:
        return {"pair": [a, b], "state": "unknown",
                "why": "cannot compare: %s" % (wa or wb)}
    only = sorted(set(sa) - set(sb))

    # ★ v2437 — AND IT STILL COULD NEVER SAY "ALIGNED". v2302 fixed the DIALECT (see _sid) and
    # the identical always-red survived one level up, through a HISTORY-vs-DISK mismatch: this
    # differenced two LIFETIME ledgers with no reference to what footage still exists.
    # MEASURED on his tree 2026-09-02:
    #
    #     chronicle entries 401 · vault entries 30 · reels on disk 40 · diverged 371
    #     of those 371 — reel directory still EXISTS: 25 · NO footage at all: 346
    #
    # The vault lane can only sweep a DIRECTORY, so 346 of them can NEVER be sealed by any
    # amount of lane work — and the count GROWS every time footage is pruned. A corroborator
    # whose red gets worse the more correctly the system behaves has stopped carrying
    # information, which is this module's own stated failure mode wearing the other colour.
    #
    # ⚠ AND A SIBLING CHECK CALLS THE SAME FACT HEALTHY: "reel extract" reports
    # "all 40 reel(s) have been read · 361 more entries retained for footage since pruned
    # (the read is the record)". 401 = 40 on disk + 361 retained. One check counted history as
    # a fault while the other counted it as the record. [[feedback-contradiction-is-the-finding]]
    #
    # So the question becomes ACTIONABLE divergence: sessions one lane covered, the other did
    # not, AND whose footage is still there for the other lane to act on. History-only entries
    # are still reported — they are not deleted from the answer, only from the verdict.
    disk, disk_why = _reels_on_disk()
    if disk is None:
        # UNKNOWN is not "no reels". Without the footage we cannot tell actionable from
        # historic, so fall back to the raw difference and SAY that is what this is.
        actionable, historic = only, None
    else:
        actionable = [s for s in only if s in disk]
        historic = [s for s in only if s not in disk]

    # ★ v2439 — THE CROSS-FAMILY EYE CRITICISED THIS SENTENCE AND IT WAS RIGHT ABOUT MY OWN FIX.
    # Asked COLD about v2437's panel text, Grok's single worst finding was:
    #
    #     "the +346 older session(s) whose footage is already gone clause. The live claim is 25
    #      sessions. The aside is a larger, unfixable historical count IN THE SAME SENTENCE, so
    #      THE NUMBER THAT WILL STICK IS THE ONE THAT CANNOT BE ACTED ON."
    #
    # v2437 fixed a panel that could not say what was wrong, and then buried the answer under a
    # bigger number nobody can do anything about. It also noted the reader could read 25 + 346 as
    # "371 broken sessions". So the historic count LEAVES the sentence: it stays in the payload as
    # `historyOnly`, where a surface that wants context can quote it, and it stops competing with
    # the only number he can act on. [[label-outlived-referent]]
    tail = ""
    if historic is None:
        # this one MUST stay in the sentence: it changes what the number MEANS, rather than
        # adding context to it. A raw difference presented as a measured one is the lie.
        tail = " (footage could not be listed: %s — so this is the raw difference)" % disk_why

    # ⚠⚠ v3266 — SPLIT "b HAS NOT SEALED IT" FROM "b OWES IT". See held_by_design: all nine of
    # his were held ON PURPOSE and the vault owed none of them, while the panel told him to sweep.
    # ⚠ owed_by is None -> UNCOUNTED, and the sentence below is left exactly as it was. Collapsing
    # an unasked question into "owes nothing" would turn this check off on every venue that cannot
    # ask. [[unknown-stays-unknown]]
    waiting, kept, orphan = actionable, [], []
    if owed_by is not None and actionable:
        waiting = [s for s in actionable if s in owed_by]
        rest = [s for s in actionable if s not in owed_by]
        _held = held if held is not None else {}
        kept = [s for s in rest if _held.get(s)]
        # ⚠ AND THE LEFTOVERS STAY RED. A reel on disk that no lane owes and no retention rule
        # names is the one real fault in this family: nothing automatic will ever deliver it, and
        # it would be the easiest thing in the world to sweep into the "held by design" bucket and
        # never see again. That is the gap he asked about — "whats not moving them along".
        orphan = [s for s in rest if not _held.get(s)]

    if waiting or orphan:
        # ⚠ THE OLD SENTENCE ASSERTED A CONSEQUENCE THAT WAS FALSE FOR 93% OF WHAT IT COUNTED.
        # It said "every one of those reels is held as 'not sealed'". Against the frame
        # deleter's own tally of 5022 held frames: NOT SEALED 1247, while the LARGEST held
        # class — 3314 — is reels the vault lane DID seal, and the 346 footage-less sessions
        # hold zero frames between them. [[label-outlived-referent]]
        # ⚠ AND IT SAYS WHAT TO DO. Grok's other findings on the v2437 text: nothing named an
        # action, and nothing said whether it needed attention now. A panel that diagnoses and
        # never prescribes leaves him to guess, which is the state this whole check replaced.
        bits = []
        if waiting:
            bits.append("%d reel(s) still on disk need a %s sweep — %s read them, %s never sealed "
                        "them, and %s's seal is the one the frame deleter reads, so they stay "
                        "held. Sweep %s to free them." % (len(waiting), b, a, b, b, b))
        if orphan:
            bits.append("%d reel(s) on disk that %s has not sealed, %s does not owe, and no "
                        "retention rule holds — nothing automatic will ever deliver them, so they "
                        "sit until someone says what to do with them." % (len(orphan), b, b))
        if kept:
            bits.append("(%d more differ but are held ON PURPOSE: %s — no sweep is owed for those)"
                        % (len(kept), _tally(kept, held or {})))
        why = " ".join(bits) + tail
    elif kept:
        # ⚠ ALIGNED, not diverged — and it must still SAY the number, or a reader who remembers
        # yesterday's "9" reads today's silence as the reels having vanished. Same number, true
        # word. [[label-outlived-referent]]
        why = ("%s has not sealed %d reel(s) still on disk and owes none of them: %s. Held on "
               "purpose — nothing is waiting." % (b, len(kept), _tally(kept, held or {}))) + tail
    else:
        why = ("%s and %s agree on every session whose footage is still on disk" % (a, b)) + tail

    return {
        "pair": [a, b], "state": ("diverged" if (waiting or orphan) else "aligned"),
        "onlyInFirst": len(only),          # unchanged meaning: the raw lifetime difference
        "actionable": len(waiting) + len(orphan),   # what somebody could still do something about
        # ⚠ published separately so a surface can show the three populations rather than one
        # number wearing whichever word was written first.
        "waiting": len(waiting),           # the lane owes these and has not done them
        "orphan": len(orphan),             # nobody owes these and nothing holds them
        "heldByDesign": len(kept),         # held on purpose; no sweep is owed
        "historyOnly": (None if historic is None else len(historic)),
        "sample": (waiting or orphan or kept or only)[:4],
        "why": why,
    }


def actionable_counts():
    """How many owed units each lane can ACTUALLY ACT ON right now. -> {lane: int or None}

    ⚠⚠ v3265 — THE THIRD STATE. `owed_counts` answers "how much is waiting"; this answers "how
    much of it can this lane touch". They are different numbers on purpose and the gap between
    them is the finding.

    MEASURED on his console, 2026-09-17, with the doctor reporting the chronicle lane STOPPED:
        owed by the loop rule   4   (reel_s_1789419985817_32179, …_1789419736164_30857,
                                     …_1789330829280_66296, …_1788993875843_44020)
        sweepable right now     0
        chronicle_sweep_now     "nothing waiting: every reel with a chosen Chronicle focus has
                                 been swept"
    The lane is neither STOPPED nor IDLE. It owes four reads and can perform none of them, because
    none of those reels has a chosen Chronicle focus — it is BLOCKED, waiting on a declaration
    nobody has made. Filing that as "STOPPED" sends him looking for a dead thread that is alive and
    correct, and filing it as IDLE would hide four reels that genuinely owe work.

    ⚠ None means NOBODY COUNTED, exactly as in `owed_counts`, and an uncounted lane keeps whatever
    verdict it had. [[unknown-stays-unknown]]
    """
    return {n: r.get("actionable") for n, r in lane_reasons().items()}


def _serving(ca):
    """The control_app SERVING this process (it runs as __main__), else the module imported. -> module

    REG-3200 - the console runs control_app.py as __main__, so `import control_app` here builds a SECOND module whose
    in-memory lane state is its literals; the hang holds and the tick's memory live in the one serving. The same rule
    console_doctor._serving_console keeps (REG-1881). [[the-unjoined-end]]"""
    m = sys.modules.get("__main__")
    if (m is not None and m is not ca and hasattr(m, "_vault_lane_reasons")
            and os.path.basename(str(getattr(m, "__file__", "") or "")) == "control_app.py"):
        return m
    return ca


def lane_reasons():
    """Per lane: how many owed units it can ACT ON now, and why not the rest. -> {lane: {actionable, why}}

    REG-3200 - THE VAULT LANE COUNTED NOTHING HERE, SO IT COULD ONLY EVER READ "STOPPED". MEASURED on his Mac
    2026-11-05: "vault: 99 session(s), last did work 194.5 h ago - past the 48 h mark, so this lane has STOPPED",
    while its own tick said "8 owed, none startable" - 7 sealed by the current reader with nothing taken (they wait
    on a new vault reader) and 1 quarantined after hanging the measurer. A lane waiting on named things is BLOCKED,
    and the sentence is the lane's own (control_app._vault_lane_reasons, the tick's one picker rule).
    None = nobody counted, which keeps the verdict the lane already had. [[unknown-stays-unknown]]"""
    out = {n: {"actionable": None, "why": None} for n in LANES}
    try:
        import control_app as _ca
    except Exception:
        return out
    try:
        w = _ca._unswept_chron_reels(limit=50)
        if isinstance(w, list):
            out["chronicle"]["actionable"] = len(w)
    except Exception:
        pass
    try:
        r = _serving(_ca)._vault_lane_reasons()
        a = r.get("actionable") if isinstance(r, dict) else None
        if isinstance(a, int) and not isinstance(a, bool):
            out["vault"] = {"actionable": a, "why": r.get("why")}
    except Exception:
        pass
    return out


def owed_counts():
    """How many units of work each lane actually has WAITING. -> {lane: int or None}

    v2301 — the input `lane()` never had. None means nobody could count it, and an uncounted lane
    stays STALLED: a lane that cannot say what it owes has not earned the word IDLE.
    [[unknown-stays-unknown]]
    """
    out = {n: None for n in LANES}
    try:
        import control_app as _ca
    except Exception:
        return out
    try:
        n = _ca._chron_owed_count()
        if isinstance(n, int):
            out["chronicle"] = n
    except Exception:
        pass
    # ⚠ BOTH LANES, OR THE ONE LEFT OUT IS A SELF-INFLICTED UNKNOWN. _vault_owed_reels already
    # existed; measuring only the chronicle would have left the vault lane reading STOPPED for ever
    # on a machine that had simply swept everything — the exact false alarm this change is for.
    # v2304 — the shadow watcher owes work exactly when the game is on screen and nothing is
    # rolling. That is the ONE state in which it is supposed to act, so it is the only state in
    # which its silence is a stall rather than a lane with nothing to do.
    try:
        st = _ca._shadow_state()
        if not st.get("on"):
            out["shadow-watch"] = 0          # switched off by him: nothing is owed, by choice
        else:
            win = None
            try:
                import tv_diablo as _tv
                win = (_tv.find_d2r_window_win() if sys.platform.startswith("win")
                       else _tv.find_d2r_window_mac())   # the door's own finder, per OS
            except Exception:
                win = "RAISED"                # could not look -> UNKNOWN below (the second eye on v3520)
            if win == "RAISED" or (win is None and getattr(_tv, "_PICK_UNKNOWN", False)):
                # the second eye on v3519: the Windows finder could not LOOK (no desktop), so whether a
                # reel is owed is UNKNOWN - never "nothing owed" [[unknown-stays-unknown]]
                out["shadow-watch"] = None
            elif win is None:
                out["shadow-watch"] = 0 if st.get("recording") else 0
            else:
                out["shadow-watch"] = 0 if st.get("recording") else 1
    except Exception:
        pass
    try:
        v = _ca._vault_owed_reels()
        if isinstance(v, (list, tuple, set)):
            out["vault"] = len(v)
        elif isinstance(v, int):
            out["vault"] = v
    except Exception:
        pass
    return out


def report(now_ms=None, owed=None, actionable=None):
    """Everything, in one object a caller can render or a gate can fail on. -> dict

    ⚠ v2308 — `owed` IS AN ARGUMENT BECAUSE MEASURING IT REACHES INTO THE LIVE TREE. v2301 called
    owed_counts() unconditionally from here, and owed_counts() imports control_app and asks the
    REAL machine. A fixture that seals a deliberately stalled lane then had its verdict decided by
    his console rather than by the fixture — the stall test went green on a tree where nothing was
    owed. A gate whose answer depends on the machine it runs on is not measuring the fixture.
    Callers that want the live picture pass nothing; tests pass what they are testing.
    [[feedback-fixtures-never-touch-live-data]]
    """
    _owed = owed_counts() if owed is None else dict(owed)
    # ⚠⚠ v3266 — v3265 CALLED actionable_counts() UNCONDITIONALLY AND RE-OPENED THE HOLE v2308
    # CLOSED FOR `owed` ONE LINE ABOVE. actionable_counts() imports control_app and asks the REAL
    # machine, so a fixture sealing a deliberately stalled lane would have had its verdict decided
    # by whatever his console happened to owe — "a gate whose answer depends on the machine it
    # runs on is not measuring the fixture", in v2308's own words, which I read while writing the
    # line that broke it. A caller supplying `owed` IS a fixture: it gets {} here, every lane
    # comes back actionable=None, and None keeps whatever verdict the lane already had.
    # [[feedback-fixtures-never-touch-live-data]] [[unknown-stays-unknown]]
    # REG-3200 - live, each lane's reasons travel with its count (one pass, never a second ask of the lane)
    _rsn = lane_reasons() if (owed is None and actionable is None) else {}
    _act = ({n: r.get("actionable") for n, r in _rsn.items()} if (owed is None and actionable is None)
            else ({} if actionable is None else dict(actionable)))
    lanes = {n: lane(n, now_ms, owed=_owed.get(n), actionable=_act.get(n),
                     blocked_why=(_rsn.get(n) or {}).get("why")) for n in LANES}
    # ⚠ same fixture discipline as `_act` above: a caller supplying `owed` is a fixture, and a
    # fixture must not have its divergence decided by his live retention plan. It gets None for
    # both, which is UNCOUNTED, which keeps the pre-v3266 sentence exactly.
    _live = (owed is None and actionable is None)
    divs = []
    for _a, _b in CORROBORATE:
        _ob = owed_sessions(_b) if _live else None
        _hd = None
        if _live:
            _sa, _ = _load(LANES.get(_a, ("", "", 0))[0])
            _sb, _ = _load(LANES.get(_b, ("", "", 0))[0])
            if _sa is not None and _sb is not None:
                _hd = held_by_design(sorted(set(_sa) - set(_sb)))
        divs.append(divergence(_a, _b, owed_by=_ob, held=_hd))
    # "idle" is a HEALTHY state: swept everything, nothing owed. Only stalled/unknown are bad.
    # ⚠⚠ v3266 — AND THE SAME OMISSION ONE LEVEL DOWN. v3265 taught `health_engine` the new
    # word and left THIS list, so `report()["ok"]` came back True for a lane owing 4 reads it
    # cannot touch. A new verdict is a join at EVERY consumer, and there were three: this list,
    # `say()`'s mark map, and health_engine. I found two of them only by grepping for the old
    # word after shipping. [[the-unjoined-end]] [[regression-guard]]
    bad = [l for l in lanes.values() if l["state"] in ("stalled", "blocked", "unknown")]
    bad += [d for d in divs if d["state"] in ("diverged", "unknown")]
    return {"ok": not bad, "lanes": lanes, "divergences": divs,
            "why": ("every lane is fresh and aligned" if not bad
                    else "; ".join(x["why"] for x in bad))}


def say(rep):
    """Lines a person reads. -> list[str]"""
    out = []
    for n, l in sorted(rep["lanes"].items()):
        # ⚠ v3266 — 🟡 is BLOCKED, deliberately not 🔴: the remedy is a declaration he has to
        # make, not a thread to restart, and painting it the same red as a dead lane is what sent
        # me hunting a dead thread in the first place. `idle` is named rather than defaulting,
        # so a state nobody thought about still lands on "·" and is visible as unnamed.
        mark = {"fresh": "🟢", "idle": "🟢", "blocked": "🟡",
                "stalled": "🔴", "unknown": "⚪"}.get(l["state"], "·")
        out.append("%s %-10s %s" % (mark, n, l["why"]))
    for d in rep["divergences"]:
        mark = {"aligned": "🟢", "diverged": "🔴", "unknown": "⚪"}[d["state"]]
        out.append("%s %-10s %s" % (mark, "+".join(d["pair"]), d["why"]))
    return out


def main(argv=None):
    rep = report()
    for line in say(rep):
        print("   " + line)
    if rep["ok"]:
        print("\n🟢 every extraction lane is doing work and they agree on what is done.")
        return 0
    print("\n🔴 an extraction lane has stopped or two lanes disagree — nothing downstream of it "
          "can be trusted to be complete.")
    return 1


if __name__ == "__main__":
    import sys
    try:
        sys.path.insert(0, HERE)
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
