#!/usr/bin/env python3
# 📼 TV DIABLO — REPLAY (v752). Re-run a REAL past session: the frames the agent archived
# (tv/frames/hist) + the reads it recorded (tv/sessions.jsonl) drip through the REAL loop
# in watch mode with TV_STUB — real photos, recorded truth, zero vision cost.
#
#   tvd replay             replay the newest journaled session
#   tvd replay --list      list journaled sessions
#   tvd replay --n 2       replay the 2nd-newest session
#   tvd replay --pace 0.8  seconds between frames (default 1.2)
#
# Honesty: the manifest is built ONLY from reads whose archived frame still exists; the
# recorded read (area/scene/names/tz/stashTab/note) is replayed verbatim — nothing invented.
import json, os, shutil, signal, subprocess, sys, tempfile, time

# v1480 — make our own output survive the operator's console before we print anything.
# A tool whose verdict is its exit code must not die reporting it (REG-044/054/077): on a Hebrew
# cp1255 console every check mark we print is an unencodable character, and the crash lands in the
# dangerous direction — a correct tree reporting FAILURE.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.environ.get("TV_SESSIONS") or os.path.join(HERE, "sessions.jsonl")   # v877 — CI harness override
HIST = os.path.join(HERE, "frames", "hist")
SESSION_GAP_MS = 10 * 60 * 1000   # ≥10min silence = a new session


def journal_paths(path=None):
    """Every file the journal is READ from, oldest first. -> [path]

    ⚠⚠ v3106 — THIS EXISTS BECAUSE THE READER AND THE WRITER DISAGREED ABOUT WHAT "THE JOURNAL" IS.
    `load_journal` has read a generation ring since v779 — `.5 … .1` then the live file — while
    `journal_retention` asked `tv_diablo.JOURNAL` and got the LIVE FILE ALONE. So the river's
    planner judged 2,895 sessions across the ring and its applier could only rewrite one file of
    it. MEASURED on his tree:

        sessions.1.jsonl   7,103 rows   2,483 sessions   <- the applier never touched this
        sessions.jsonl     5,093 rows     357 sessions   <- the only file it rewrote

    Every release against a session living in the rotated half was a silent no-op, which is the
    whole reason the river could not drain. One function, asked by both ends.
    [[copy-drift]] [[the-unjoined-end]]

    ⚠ IT RETURNS THE PATHS THAT EXIST, in read order. A caller that needs "what would be read"
    gets exactly that, and cannot drift from what `load_journal` does one line below.
    """
    if path is not None:
        return [path]
    _root, _ext = os.path.splitext(JOURNAL)
    # v811 — generation ring: oldest first (.5 … .1), then the live file
    ring = [_root + ".%d" % g + _ext for g in range(5, 0, -1)] + [JOURNAL]
    return [p for p in ring if os.path.exists(p)]


def load_journal(path=None):
    # v779 (Grok R5/R7) — read the ROTATED half first, then the live file, concatenated in
    # chronological order, so a rotation (sessions.jsonl → sessions.1.jsonl) never hides history.
    paths = journal_paths(path)
    reads = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:                       # torn/empty line — skip, never break loading
                        continue
                    try:
                        reads.append(json.loads(line))
                    except Exception:
                        pass                           # partial JSON from a mid-write crash — skip
        except FileNotFoundError:
            pass
    return reads


def row_moment(r):
    """REG-2736 (#86) - WHEN A JOURNAL ROW HAPPENED: its frame's capture time when it carries one, else its ts. -> int

    `ts` is when the row was WRITTEN. For a live read the two are seconds apart; for a re-read of an old reel they are
    days apart. MEASURED 2026-10-28 on his journal: the KAI closer's re-closes of 12 October reels (REG-2728) wrote
    intake, kai and watchdog rows with ts = today - every one carrying its frame's captureTs - and the Shelf, which
    ordered and dated sessions by ts, put an October 10 reel first, called it the LAST SESSION, and gave it a 17-day
    read span. A session is ordered and dated by when its moments were captured."""
    c = (r or {}).get("captureTs")
    if isinstance(c, (int, float)) and not isinstance(c, bool) and c > 0:
        return int(c)
    t = (r or {}).get("ts")
    return int(t) if isinstance(t, (int, float)) and not isinstance(t, bool) and t > 0 else 0


#: REG-2736 - lanes that ANNOTATE a session after it: the KAI closer's ledger ("KAI closed the session ...") and the
#: watchdog's verdict. They say when the note was written, not when anything in the session happened - and each re-close
#: dated its note from the session's newest row, the last note, so 59 re-closes walked one September reel to today.
POST_HOC_LANES = ("kai", "watchdog")


#: REG-2744 (the v3821 second eye) - lanes that read a session's frames AGAIN, later: their row is a moment of the session
#: only through the frame's capture time. Without one, its ts is when the re-read wrote, and that moved t0/t1 and the
#: order exactly as the KAI notes had (REG-2736). Measured on his journal 2026-10-28: all 965 intake and 7 verify rows
#: carry captureTs, so nothing moves today; this closes the door before a row without one arrives.
REREAD_LANES = ("verify", "intake")


def _session_moment(r):
    """A row's moment for dating its session: a re-read lane counts by its frame's capture time alone. -> int (0 = none)"""
    if (r or {}).get("lane") in REREAD_LANES:
        cap = r.get("captureTs") if isinstance(r, dict) else None
        return int(cap) if isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0 else 0
    return row_moment(r)


def session_moments(g):
    """REG-2736 - the moments a session's own rows were captured (row_moment), the post-hoc notes left out; every row's
    when nothing else is there. REG-2744 - a re-read lane's row counts only through its capture time. REG-2752 (the v3823
    second eye) - and the fallback keeps that: a re-read row with no capture time is never a moment, so a session made of
    nothing else has none (its date is UNKNOWN, never the day the re-read wrote). -> [int]"""
    m = [x for x in (_session_moment(r) for r in (g or []) if (r or {}).get("lane") not in POST_HOC_LANES) if x > 0]
    return m or [x for x in (_session_moment(r) for r in (g or [])) if x > 0]


def split_sessions(reads):
    """Chronological journal → list of sessions (newest first).

    v780 — prefer explicit sessionId (one ON cycle = one theatre reel). Fall back to the
    classic ≥10min silence split for pre-v780 journal rows that lack sessionId.

    ⚠⚠ v3060 — A REEL IS ALL ITS ROWS, HOWEVER THEY INTERLEAVE. This used to cut a new session
    whenever sessionId differed from the IMMEDIATELY PRECEDING row. Two reels recording
    concurrently interleave by timestamp, so A,B,A emitted THREE groups and one reel became
    several "sessions".

    MEASURED on his journal, 2026-09-13:

        journal rows                    11,162
        contiguous runs                  3,129
        session rows the shelf rendered  3,128   <- exactly the runs
        sessionIds in MORE THAN ONE run    176
        worst reel                          16 runs

    straight from the journal, two reels alternating:

        run 2425  s_1787522893554_13522   101 rows
        run 2426  s_1787523300658_1         3 rows
        run 2427  s_1787522893554_13522     3 rows
        run 2428  s_1787523300658_1         2 rows

    ⚠ AND IT BROKE PLAYBACK, NOT JUST THE COUNT. Each fragment carried its OWN share of the
    frames, so one reel read `frames=10` in one row and `frames=0` in another while 19 stills
    sat on disk. He opened the row that said 0 and the player had nothing to play; the arrow
    stepper reads the reel directly and worked. Same reel, two answers, and he got the empty
    one. It is also why the card said "19 frames" and the dossier said "0 FRAMES".

    ⚠ THE UNSTAMPED HISTORY KEEPS THE OLD RULE. Rows with no sessionId predate v780 and have
    nothing to group ON, so they still split on ≥10min silence. Grouping them by absence would
    fuse years of history into one enormous session.

    Measured after this change, against the same journal: groups 3128 → 2893, duplicated
    sessionIds 175 → 0, worst reel 16 groups → 1 with all 516 rows intact, and every one of the
    11,162 rows preserved — same row set in, same row set out, none lost and none invented.
    [[the-unjoined-end]] [[label-outlived-referent]]
    """
    srt = sorted(reads, key=lambda x: x.get("ts") or 0)
    by_sid, unstamped = {}, []
    for r in srt:
        sid = r.get("sessionId") or None
        if sid:
            by_sid.setdefault(sid, []).append(r)
        else:
            unstamped.append(r)

    sessions, cur, last_ts = [], [], None
    for r in unstamped:
        ts = r.get("ts") or 0
        if cur and last_ts is not None and ts - last_ts > SESSION_GAP_MS:
            sessions.append(cur)
            cur = []
        cur.append(r)
        last_ts = ts
    if cur:
        sessions.append(cur)

    sessions.extend(by_sid.values())
    # newest first, by when each session STARTED - v3857 item 20 (#230, Elad 2026-11-03): the row is labelled by its
    # start, so a list ordered by the end put a long early run above a later one and read out of order. REG-2736 still
    # holds: the moment is when its rows were CAPTURED (session_moments), so a re-read of an old reel never jumps up.
    sessions.sort(key=lambda g: min(session_moments(g) or [0]))
    sessions.reverse()
    return sessions


def build_manifest(reads, frames_dir):
    """Recorded reads → (stub manifest keyed by frame basename, playback order).
    Only reads whose archived frame file still exists make the cut — never invent."""
    man, order = {}, []
    for r in reads:
        fid = r.get("frameId") or ""
        if not fid:
            continue
        base = fid + ".jpg"
        if not os.path.exists(os.path.join(frames_dir, base)):
            continue
        # LAST row wins per frame (an OCR/provisional glimpse is followed by the deep truth);
        # playback order = first appearance, so the run replays in real sequence.
        man[base] = {
            "area": r.get("area", ""), "scene": r.get("scene", "gameplay"),
            "names": r.get("names", []), "tz": r.get("tz", []),
            "conf": r.get("conf", 1.0),
            "stashTab": r.get("stashTab", ""),
            "note": r.get("note", ""), "transition_from": r.get("transition_from", ""),
        }
        if base not in order:
            order.append(base)
    return man, order


def main():
    args = sys.argv[1:]
    pace = 1.2
    pick = 1
    if "--pace" in args:
        pace = float(args[args.index("--pace") + 1])
    if "--n" in args:
        pick = int(args[args.index("--n") + 1])
    sessions = split_sessions(load_journal())
    if "--list" in args:
        if not sessions:
            print("📼 no journaled sessions yet — run `tvd` once, then replay")
            return
        for i, sess in enumerate(sessions, 1):
            t0 = time.strftime("%m/%d %H:%M", time.localtime((sess[0].get("ts") or 0) / 1000))
            areas = [r.get("area") for r in sess if r.get("area")]
            named = sum(1 for r in sess if r.get("names"))
            print(f"  --n {i} · {t0} · {len(sess)} reads · {named} named · "
                  + (" → ".join(dict.fromkeys(areas)) if areas else "(no areas)"))
        return
    if not sessions:
        print("📼 no journaled sessions yet — run `tvd` once (the journal starts at v752), then replay")
        sys.exit(1)
    if pick > len(sessions):
        print(f"⛔ only {len(sessions)} journaled session(s) — see `tvd replay --list`")
        sys.exit(1)
    sess = sessions[pick - 1]
    man, order = build_manifest(sess, HIST)
    if not order:
        print("⛔ that session's frames are gone from tv/frames/hist — nothing real to replay")
        sys.exit(1)

    tmp = tempfile.mkdtemp(prefix="tvd_replay_")
    watch = os.path.join(tmp, "watch")
    os.makedirs(watch)
    man_path = os.path.join(tmp, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(man, f)

    t0 = time.strftime("%m/%d %H:%M", time.localtime((sess[0].get("ts") or 0) / 1000))
    print(f"📼 REPLAY — session of {t0} · {len(order)} real frames · recorded reads · pace {pace}s")
    print("   real screenshots from tv/frames/hist through the REAL loop — flip the TV switch and watch")

    env = dict(os.environ, TV_STUB="1", TV_STUB_MANIFEST=man_path, TV_FRAMES_DIR=watch,
               TV_OCR="0",        # recorded truth only — the OCR lane would garble over replayed pixels
               TV_NO_JOURNAL="1")  # a replay never journals itself as a new session
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "tv_diablo.py"), "--watch"], env=env)
    try:
        time.sleep(2.0)   # agent boot
        for i, base in enumerate(order, 1):
            if proc.poll() is not None:
                print("⛔ agent exited early"); break
            shutil.copy2(os.path.join(HIST, base), os.path.join(watch, base))
            rd = man[base]
            tag = rd.get("scene", "?") + (" · " + ", ".join(rd["names"][:3]) if rd.get("names") else "")
            print(f"  📼 {i}/{len(order)} {base} · {tag}")
            time.sleep(pace)
        if "--exit-after" in args:
            time.sleep(float(args[args.index("--exit-after") + 1]))
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=95)
        else:
            print("📼 replay finished — Ctrl-C stops the agent (farewell read included)")
            proc.wait()
    except KeyboardInterrupt:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=95)
        except Exception:
            proc.kill()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
