# -*- coding: utf-8 -*-
"""Drain a handoff queue in O(new), not O(all) — and never lose a brief to a watermark.

Measured 2026-09-18, the reason this exists: issue #180 held 1,177 comments / 2.55 MB, and 140
comments (536 KB) arrived in one day against 10 replies. `gh issue view --comments` fetches the
WHOLE history to show the newest, so every drain paid 2.55 MB to read 6 new briefs. A queue that
expensive to read stops being read, which is exactly what happened.

This reads only what arrived since the last watermark, using the REST `since` parameter, and it
sorts the ASK / ACT lines to the top because the old format buried them under the evidence.

⚠ THE WATERMARK MOVES ONLY WHEN YOU SAY SO (`--mark`). Draining does NOT advance it. A drain that
silently marked-as-read would lose every brief that arrived while the reader was mid-answer, and an
unanswered brief that no longer appears is worse than a noisy queue — it is a queue that lies.
[[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from console_safe import enable as _cs
    _cs()
except Exception:
    pass

REPO = "KonyoDigital/d2r-bible-tests"
HERE = os.path.dirname(os.path.abspath(__file__))
MARKS = os.path.join(HERE, ".handoff_seen.json")

#: The lead-line verbs of protocol v2. ACT and ASK are owed an answer; FYI is not.
OWED = ("ACT", "ASK")


def _gh(path, method=None, fields=None, timeout=None, paginate=True):
    # ⚠⚠ v3462 — `gh` HAS NO DEADLINE OF ITS OWN, so a GitHub stall became a CALLER stall. The
    # console_doctor lane row shells through here on a timer; unbounded, one hung call would hold
    # up a doctor tick. Bounded HERE rather than in the caller, because a caller that bypasses this
    # function to add its own timeout also bypasses the utf-8 decode and the empty-stdout refusal
    # below — which is exactly what the first cut of that row did, and it silently made every test
    # stub inert and put a real network call inside the suite. One owner for the read.
    # v3866 (REG-3217) - paginate=False asks ONE page: the board's "newest successful Publish run" asks per_page=1,
    # and --paginate would walk every run GitHub keeps
    cmd = ["gh", "api", path] + (["--paginate"] if paginate else [])
    if method:
        cmd = ["gh", "api", "-X", method, path]
    for k, v in (fields or {}).items():
        cmd += ["-f", "%s=%s" % (k, v)]
    # ⚠⚠ v3395 — `text=True` DECODES WITH THE LOCALE CODE PAGE, NOT UTF-8. On his Windows box
    # (cp1255) a GitHub comment containing one non-ASCII byte killed the reader thread with
    # UnicodeDecodeError, communicate() handed back EMPTY stdout with returncode 0, and this
    # function returned [] — which the drain then printed as "nothing new. That is a measured
    # zero, not a failure to look." It was exactly a failure to look.
    # ⚠ This same file already passes encoding="utf-8" at three OTHER sites; the one call that
    # talks to GitHub was the one that did not. [[copy-drift]] [[zero-needs-a-denominator]]
    p = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "").strip()[:300])
    body = (p.stdout or "").strip()
    if not body:
        # ⚠⚠ AN EMPTY STDOUT IS NOT AN EMPTY RESULT SET. `gh api` prints `[]` for a query that
        # matches nothing, so a SUCCESSFUL call that printed nothing at all did not answer —
        # the read failed. Returning [] here is what let a dead reader reach a sentence that
        # ASSERTS it is not a failure to look. Fixing the decode above closes the known cause;
        # this closes the CLASS, because any future reader failure lands here too.
        if method:
            return []          # a write (-X POST/PATCH) may legitimately print nothing
        raise RuntimeError(
            "gh exited 0 but printed nothing for %s — an empty stdout is not an empty result "
            "set (gh prints [] for that), so this read FAILED and must not be reported as a "
            "measured zero" % path)
    # ⚠ --paginate CONCATENATES JSON DOCUMENTS with no separator, and they may be pretty-printed,
    # so neither splitlines() nor a "][" replace is safe: a fragment can parse as a bare int and
    # sail through as a "row". That is exactly how the first cut produced
    # `'int' object has no attribute 'get'` on #179 — a parse error wearing the costume of data.
    # raw_decode walks the stream one complete document at a time. [[unknown-stays-unknown]]
    dec = json.JSONDecoder()
    out, i, n = [], 0, len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        try:
            got, i = dec.raw_decode(body, i)
        except ValueError:
            break
        for row in (got if isinstance(got, list) else [got]):
            if isinstance(row, dict):
                out.append(row)
    return out


def _marks():
    """-> dict of watermarks, or None when the store cannot be READ.

    ⚠⚠ v3325 — ABSENT AND UNREADABLE ARE DIFFERENT FACTS, and collapsing them here is destructive
    rather than merely vague. `--mark` does `marks = _marks()`, adds one key, and writes the WHOLE
    DICT BACK. Returning {} for a corrupt or unreadable file therefore writes {} + one key OVER A
    GOOD STORE, destroying every other watermark — in the tool that drains his queue.
    MEASURED 2026-09-18: tv/.handoff_seen.json holds keys 179, 180, 230; the path was LATENT, not
    fired. The rule is the one `_vault_autoread_save` already earned: never write memory over a
    store this process has not read. [[unknown-stays-unknown]]
    """
    try:
        with io.open(MARKS, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    # ⚠⚠ v3355 — `FileNotFoundError`, NOT `IOError`. In Python 3 `IOError is OSError` (measured
    # True), so `except IOError` also catches PermissionError, IsADirectoryError and EMFILE — an
    # EXISTING, GOOD store that merely cannot be READ took the ABSENT arm and this returned {}.
    # MEASURED on a real file holding watermarks 179, 180 and 230 at mode 000: `_marks()` gave {}
    # and `--mark` would then write {"999": 1} over it, destroying all three — the exact wipe the
    # docstring above says must never happen, surviving inside the fix written to prevent it and
    # separated from it only by an errno the `except` clause cannot see.
    # ⚠ The second arm's comment said "malformed/unreadable" and only MALFORMED ever reached it:
    # a JSON error is a ValueError, an unreadable FILE is an OSError. Now both land there.
    except FileNotFoundError:
        return {}            # absent: nothing marked yet, and that IS a measurement
    except Exception:
        return None          # malformed OR unreadable: UNKNOWN


#: ⚠⚠ 2026-09-27 — THE SEAT TAG IS THE FIRST LINE, SO THE VERB IS THE SECOND. CLAUDE.md §4: "the TAG ON THE FIRST
#: LINE is the only thing that identifies a seat" - and this read the FIRST line for the verb. Every GrokBot comment
#: opens "GB-L", so every ACT it ever posted was filed "pre-v2 (no lead verb)" and the LANES hook said "0 ACT/ASK owed"
#: while two ACTs for Claude sat unread on 2026-09-27 (5854814442, 5855160685). A bare seat tag, or a routing header
#: ("GB-L-n — GrokBot → Claude"), is skipped; the next line carries the verb. The same gap remained
#: for the other two openers on #230, "CLAUDE → GB-L" and "GROK → GB-L": the ACT under them was still
#: pre-v2. The arrow is what makes those a tag. [[the-unjoined-end]]
# GB-L, "GB-L-n — …", and the other seats' tags ("CLAUDE → GB-L", "GROK → GB-L"). A line that
# merely starts with the word CLAUDE or GROK is not a tag — the arrow is what makes it one.
_SEAT_TAG_RX = re.compile(
    r"^(?:GB-[A-Z0-9]+(?:-[A-Z0-9]+)*(?:\s+[—–-]\s+.*)?"
    r"|(?:CLAUDE|GROK)\s*(?:→|->)\s*\S.*)$",
    re.I)
#: an OBSERVATION owes nothing: GrokBot's standing ticks lead LOOKED or STATE, and they are read, never answered.
_OBSERVED = ("LOOKED", "STATE")


#: 2026-09-28 — WHO an ACT/ASK is FOR. The routing header reads "SENDER → SEAT"; the hook counted every ACT as owed
#: by Claude, so 14 instructions Grok and Claude had written TO GrokBot ("GROK → GB-L / ACT — read the live console")
#: read as 14 things Claude owed. A body addressed to the GrokBot seat is that seat's to answer.
_ROUTE_RX = re.compile(r"^(?:CLAUDE|GROK|GB-[A-Z0-9]+(?:-[A-Z0-9]+)*)\s*(?:→|->)\s*(\S+)", re.I)
_OTHER_SEAT_RX = re.compile(r"^(?:GB-|GROKBOT)", re.I)


def _addressee(body):
    """-> the seat named after the arrow on the routing header, or None when the body has no routing header."""
    for raw in (body or "").splitlines():
        line = raw.strip().lstrip("#* ").strip()
        if not line or line.startswith("```"):
            continue
        m = _ROUTE_RX.match(line)
        return m.group(1).upper() if m else None
    return None


def owed_here(body):
    """True when this body is an ACT/ASK the code seat owes an answer to (not one addressed to GrokBot)."""
    if _classify(body)[0] not in OWED:
        return False
    to = _addressee(body)
    return not (to and _OTHER_SEAT_RX.match(to))


def _classify(body):
    """-> ('ACT'|'ASK'|'FYI'|'?', first_meaningful_line). Protocol v2 leads with the verb - after the seat tag."""
    first = next((r.strip() for r in (body or "").splitlines() if r.strip()), "")
    if first.upper().startswith("SECOND-EYE"):
        # 2026-09-28 — a second-eye post is a RECORD of a look (version · sha · verdict), read and never answered
        return "FYI", first[:200]
    skipped = 0
    for raw in (body or "").splitlines():
        line = raw.strip().lstrip("#* ").strip()
        if not line or line.startswith("```"):
            continue
        # a leading emoji or symbol is decoration ("👀 LOOKED ·", "📍 STATE —"), never the verb
        while line and not line[0].isalnum():
            line = line[1:].lstrip()
        if not line:
            continue
        if skipped < 2 and _SEAT_TAG_RX.match(line):
            skipped += 1
            continue
        head = line.upper()
        for verb in ("ACT", "ASK", "FYI"):
            if head.startswith(verb) and not head[len(verb):len(verb) + 1].isalnum():
                return verb, line[:200]
        for obs in _OBSERVED:
            if head.startswith(obs) and not head[len(obs):len(obs) + 1].isalnum():
                return "FYI", line[:200]
        # pre-v2 briefs: no lead verb. Say so rather than guessing a priority.
        return "?", line[:200]
    return "?", "(empty body)"


def _new_rows(issue, since=None):
    """-> (rows new since the watermark, the `since` used, marks_readable). ONE decision for
    drain() and summary(), so the hook's count and the reader's list can never disagree."""
    marks = _marks()
    readable = marks is not None
    marks = marks or {}
    key = str(issue)
    since = since or marks.get(key, {}).get("ts")
    path = "repos/%s/issues/%s/comments?per_page=100" % (REPO, issue)
    if since:
        path += "&since=%s" % since
    rows = _gh(path)
    # ⚠ GITHUB'S `since` IS INCLUSIVE, so the very comment the watermark points AT comes back as
    # "new" on every drain. Left alone this queue reads "1 new" forever — and a queue that is never
    # empty is one a reader learns to skip, which is the exact habit this tool exists to break.
    # Drop the watermarked id explicitly rather than nudging the timestamp, because a nudge would
    # silently swallow anything posted inside the same second. [[zero-needs-a-denominator]]
    _mark = marks.get(key) or {}
    _seen_id, _seen_upd = _mark.get("id"), _mark.get("updated")
    if _seen_id is not None:
        # ⚠ EXCLUDE IT ONLY IF IT HAS NOT CHANGED SINCE. Protocol v2 has each seat EDIT one rolling
        # `📍 STATE` comment, and GitHub's `since` filters on UPDATED — so a watermarked comment
        # that is later edited is NEW INFORMATION. A blanket exclude-by-id would hide every future
        # edit of whichever comment the watermark happened to land on: a filter that silently drops
        # real content, which is the same class of defect this tool exists to surface.
        rows = [c for c in rows
                if c.get("id") != _seen_id
                or (_seen_upd is not None and c.get("updated_at") != _seen_upd)]
        # ⚠ 2026-09-28 — AND EVERY OLDER COMMENT FROM THE SAME SECOND. Three second-eye posts landed at
        # 13:22:17; the mark named the last, and the hook said "2 NEW" on every prompt for the two before it.
        # GitHub ids only grow, so a lower id was created before the watermarked comment; it is excluded unless
        # it was EDITED after the mark (updated_at later than the mark's time), which is new information.
        if isinstance(_seen_id, int) and since:
            rows = [c for c in rows
                    if not (isinstance(c.get("id"), int) and c["id"] < _seen_id
                            and (c.get("updated_at") or "") <= since)]
    rows.sort(key=lambda c: c.get("created_at") or "")
    return rows, since, readable


def drain(issue, since=None, limit=40):
    rows, since, readable = _new_rows(issue, since)
    if not readable:
        # UNKNOWN watermark: drain from the beginning, and SAY so. Silently starting at zero
        # reads as "the queue is enormous" rather than "the store could not be read".
        print("⚠ the watermark store could not be READ — draining #%s from the beginning. "
              "That is UNKNOWN, not an empty queue." % issue)

    print("queue #%s — %d new since %s" % (issue, len(rows), since or "THE BEGINNING (no watermark)"))
    if not since:
        print("  no watermark set. This is every comment on the issue, not a delta.")
    if not rows:
        print("  nothing new. That is a measured zero, not a failure to look.")
        return rows

    buckets = {"ACT": [], "ASK": [], "FYI": [], "?": []}
    for c in rows:
        verb, lead = _classify(c.get("body"))
        buckets[verb].append((c, lead))

    _here = sum(1 for c in rows if owed_here(c.get("body")))
    print("  %d ACT · %d ASK · %d FYI · %d pre-v2 (no lead verb) — %d owed HERE (the rest are addressed to "
          "another seat)" % (len(buckets["ACT"]), len(buckets["ASK"]), len(buckets["FYI"]), len(buckets["?"]), _here))
    shown_ids = set()
    for verb in ("ACT", "ASK", "?", "FYI"):
        got = buckets[verb]
        if not got:
            continue
        print("\n── %s ──" % verb)
        for c, lead in got[:limit]:
            print("  #%s  %s  %s" % (c.get("id"), (c.get("created_at") or "")[:16], lead))
            shown_ids.add(str(c.get("id")))
        if len(got) > limit:
            print("  … +%d more not listed (raise --limit)" % (len(got) - limit))

    # ⚠⚠ THE SECOND EYE ON 4a222c64 (grok-4.7), reproduced from the code: this recorded rows[-1] -
    # the newest comment OVERALL - as shown, even when a bucket longer than --limit had just printed
    # "+N more not listed". --mark then advanced through it and filed the unlisted tail as read. A
    # watermark is ONE point in time, so it may only go as far as the last comment before the FIRST
    # one that was not put in front of the reader. [[the-unjoined-end]]
    upto = None
    for c in rows:                      # chronological (_new_rows sorts)
        if str(c.get("id")) not in shown_ids:
            break
        upto = c
    newest = rows[-1]
    if upto is not None:
        _record_shown(issue, upto)
    if upto is not newest:
        print("\n  ⚠ --mark will stop at %s: comments after it were NOT listed (raise --limit to see them)"
              % (("#%s" % upto.get("id")) if upto is not None else "nothing - the oldest was not listed"))
    print("\n  newest: #%s at %s" % (newest.get("id"), newest.get("created_at")))
    print("  answer the ACT/ASK rows, then: handoff.py --issue %s --mark" % issue)
    print("  ⚠ the watermark has NOT moved — draining never marks anything read.")
    return rows


def summary(issue):
    """ONE line for the prompt hook. -> str. Never raises: a failed read says UNKNOWN.

    ⚠⚠ WHY THIS EXISTS (2026-09-24): #230 carried eight GrokBot ticks and #231 five second-eye looks
    between 05:06Z and 07:03Z, and I read none of them for two hours — the drain existed, the
    watermark said 2026-09-23 21:26Z, and nothing ever RAN it. He asked for it to be part of the
    system: *"make it a part of your system regularly to check it always"*. So a UserPromptSubmit
    hook calls this on every prompt, and the count stays in front of the reader until `--mark`.
    [[the-unjoined-end]] [[feedback-silence-is-not-evidence]]"""
    try:
        rows, since, readable = _new_rows(issue)
    except Exception as e:
        return "#%s: UNKNOWN — the queue could not be read (%s)" % (issue, str(e)[:80])
    if not readable:
        return "#%s: UNKNOWN — the watermark store could not be READ" % issue
    if not rows:
        return "#%s: nothing new since %s (a measured zero)" % (issue, since or "the beginning")
    owed = sum(1 for c in rows if owed_here(c.get("body")))
    return ("#%s: %d NEW since %s (%d ACT/ASK owed) · newest %s — read them: handoff.py --issue %s, "
            "then --mark" % (issue, len(rows), since or "THE BEGINNING (no watermark)", owed,
                            (rows[-1].get("created_at") or "?")[:16], issue))


def _record_shown(issue, row):
    """Remember the newest comment a drain PUT IN FRONT OF THE READER. `--mark` marks through it."""
    marks = _marks()
    if marks is None:
        return                      # never write over a store this process could not read
    marks["%s:shown" % issue] = {"id": row.get("id"), "ts": row.get("created_at"),
                                 "updated": row.get("updated_at")}
    with io.open(MARKS, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(marks, indent=2, sort_keys=True))


def mark(issue, through=None):
    """Advance the watermark through what the reader SAW — never through what merely exists.

    ⚠⚠ MEASURED 2026-09-24 07:09Z, the first time `--mark` was run on this tree in a day: it marked
    #230 through comment 5809493768, a GrokBot tick posted AFTER the listing I had read, so a tick
    nobody had seen was filed as read — the exact loss this module's docstring says a drain must
    never cause, done by the marker instead. It took `rows[-1]` at MARK time. Now it marks through
    `through` when given, else through the newest comment the last drain SHOWED, and names every
    newer comment it did not mark. With neither, it refuses. [[the-unjoined-end]]"""
    rows = _gh("repos/%s/issues/%s/comments?per_page=100" % (REPO, issue))
    if not rows:
        print("no comments; watermark unchanged.")
        return
    rows.sort(key=lambda c: c.get("created_at") or "")
    marks = _marks()
    if marks is not None and through is None:
        through = (marks.get("%s:shown" % issue) or {}).get("id")
        if through is None:
            print("⚠ REFUSED to mark #%s: nothing has been SHOWN since the last mark. Drain it first "
                  "(handoff.py --issue %s), or name the last comment you read: --through <id>."
                  % (issue, issue))
            return
    hit = [i for i, c in enumerate(rows) if str(c.get("id")) == str(through)]
    if marks is not None and not hit:
        print("⚠ REFUSED to mark #%s: comment %s is not on the issue." % (issue, through))
        return
    newest = rows[hit[0]] if hit else rows[-1]
    later = rows[hit[0] + 1:] if hit else []
    if marks is None:
        # ⚠⚠ REFUSE, DO NOT OVERWRITE. Writing here would replace a store this process could not
        # read with {} plus one key, and the file would then look authoritative — strictly worse
        # than not marking at all. [[unknown-stays-unknown]]
        print("⚠ REFUSED to advance the watermark: %s could not be READ, and writing now would "
              "destroy every other issue's mark. Fix or remove the file, then re-run." % MARKS)
        return
    marks[str(issue)] = {"id": newest.get("id"), "ts": newest.get("created_at"),
                         "updated": newest.get("updated_at")}
    marks.pop("%s:shown" % issue, None)
    with io.open(MARKS, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(marks, indent=2, sort_keys=True))
    print("watermark for #%s -> %s (#%s)" % (issue, newest.get("created_at"), newest.get("id")))
    if later:
        print("  ⚠ %d newer comment(s) NOT marked — they arrived after what you read: %s"
              % (len(later), ", ".join("#%s %s" % (c.get("id"), (c.get("created_at") or "")[11:16])
                                       for c in later[:6])))


def archive(issue, path):
    rows = _gh("repos/%s/issues/%s/comments?per_page=100" % (REPO, issue))
    rows.sort(key=lambda c: c.get("created_at") or "")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rows, indent=1, sort_keys=True, ensure_ascii=False))
    total = sum(len(c.get("body") or "") for c in rows)
    print("archived %d comment(s), %s body bytes -> %s" % (len(rows), format(total, ","), path))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # ⚠⚠ THE LEGACY QUEUES ARE STILL DRAINED, AND THAT IS NOT BELT-AND-BRACES. #179/#180 were
    # rotated CLOSED on 2026-09-18 — but GitHub ACCEPTS COMMENTS ON CLOSED ISSUES, and the seats
    # post from their own schedulers which may still name the old number. Draining only #230 would
    # report a confident "0 new" while briefs piled into a thread nobody reads: a rotation that
    # orphans the far end is the-unjoined-end wearing a tidy-up costume, and the zero would look
    # exactly like peace. Drop a legacy id only once that seat has been SEEN posting to #230.
    ap.add_argument("--issue", default="230,180,179",
                    help="comma-separated; 230 is the live queue, 180/179 are closed but still "
                         "writable and are drained until each seat is seen to have moved")
    ap.add_argument("--since", default=None, help="ISO8601; overrides the stored watermark")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--mark", action="store_true", help="advance the watermark to the newest comment")
    ap.add_argument("--archive", metavar="PATH", help="write every comment to PATH as JSON")
    ap.add_argument("--through", default=None,
                    help="with --mark: the id of the last comment you actually read")
    ap.add_argument("--summary", action="store_true",
                    help="one line per queue (new count, ACT/ASK owed, newest) — the prompt hook")
    a = ap.parse_args(argv)

    issues = [i.strip() for i in str(a.issue).split(",") if i.strip()]
    if a.summary:
        for i in issues:
            print(summary(i))
        return 0
    if a.archive:
        for i in issues:
            archive(i, a.archive if len(issues) == 1 else "%s.%s" % (a.archive, i))
        return 0
    if a.mark:
        if a.through and len(issues) != 1:
            print("⚠ --through names ONE comment, so it needs exactly one --issue.")
            return 2
        for i in issues:
            mark(i, through=a.through)
        return 0
    live = 0
    for i in issues:
        rows = drain(i, since=a.since, limit=a.limit)
        live += len(rows or [])
        print("")
    if live == 0:
        print("all %d queue(s) quiet — a measured zero across every one, legacy included."
              % len(issues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
