#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A7·ROUTE — ONE STATION PER REEL, DERIVED FROM THE REEL'S OWN EVIDENCE.

His ask, 2026-09-05: *"we want a unified logic for all reels no gaps.. they all get run through
the processing system we built where is station and the printer to get filtered through the heart
and console and eventually end up in their individual routes"* and, when I showed him the
measurement: *"the routing system can be placed after the reels get filtered and still end up
where they are. just the gates placed accordingly."*

⚠⚠ THE DEFECT THIS EXISTS FOR, MEASURED 2026-09-05 ON HIS SHELF. 40 reels, 29 with no journal row
at all, and the oldest ten — back to 2026-07-25 — all unread. It is not that the queue is ordered
badly. **There is no queue.**

    chronicle_autoread_tick   takes the 12 NEWEST journal visits and carries an explicit
                              `if v.get("source") == "reel": continue`. Journal-only BY DESIGN.
    vault_autoreel_tick       is the reel reader. It takes `_vault_owed_reels()`, which returns
                              only reels retention tags `vault-owes`. MEASURED: 0 of 40.

`_vault_owed_reels()` is first-match-wins and `vault-owes` is the LAST rule, so every reel matches
something earlier — `zero-pages` 28, `test-fixture` 7, `recent` 5, `vault-owes` **0**. The lane
picks nothing, forever, and publishes `owed: 0`, which reads as a healthy idle lane.

⚠ THE CODE ALREADY SAID SO and filed it as latent: *"The `vault-owes` tag genuinely never fires on
his tree because earlier rules match first. That is a LATENT defect the day a reel legitimately
reaches it."* It is not latent. It is what is starving 29 reels, and it is starving the BIGGEST
ones — unread reels run to 2,387 frames while no reel that WAS read exceeds 134.

⚠⚠ AND THE ROOT IS ONE QUESTION DOING TWO JOBS. `reel_story._stage_of(tag)` derives a reel's
STAGE from the RETENTION TAG, and `printer.stream()`'s route field is literally the tag glued to
the verdict (`"test-fixture@releasable"`). So *do we keep these bytes* and *where is this reel in
the river* are answered by one value. Collapsing them lets the keep-reason silently decide the
read-fate, which is [[unknown-stays-unknown]] §2 — two questions wearing one name. Measured
consequence: all 40 reels sit at TWO of `reel_story`'s six stages (`swept` 28, `releasable` 12);
`filmed`, `triaged`, `banked` and `vault-done` are permanently EMPTY.

WHAT THIS MODULE DOES, AND THE LINE IT WILL NOT CROSS:

  · it assigns exactly ONE station per reel, from the reel's OWN evidence — surveyed, names read,
    sealed — and NEVER from the retention tag. `assert_independent_of_retention()` is the guard.
  · every reel on the shelf gets a station. UNKNOWN is a station, not a gap, and is never folded
    into a working total. The invariant `counts sum to shelf size` is asserted, not hoped for.
  · `owed(station)` orders oldest-first — FIFO, by the reel's own capture clock — because that is
    what he asked for and what the frame counts say is being starved.

⚠⚠ IT ARMS NOTHING AND IT DELETES NOTHING. It publishes a queue; it does not consume one. Wiring
a reader to `owed("STATION")` would start **13 paid sweeps** on his money, and the 2026-08-28
incident was exactly that — a predicate that read as equivalent queued 19 reels where retention
said 2, three of them test fixtures. That wiring is a separate, gated decision and it is HIS.
**The prune stays OFF; this routes and stamps, it never removes.** [[borrowed-surface]]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: The river, in order. A reel's station is its POSITION; what it OWES is the named gate in front
#: of it. Keeping those separate is the whole point — two reels can sit at the same position and
#: owe different work, and one word for both is how `route` became the retention tag.
STATIONS = ("INTAKE", "TRIAGE", "EMPTY", "STATION", "PRINTER", "JOIN", "CAPTURE",
            "ROUTED", "TOMBSTONE")

#: REG-1678 (2026-10-01) — the stations where NO READ IS OWED: the survey found no panel (EMPTY), the reader
#: yielded no name from a sealed reel (CAPTURE), or the river closed it (ROUTED, TOMBSTONE). The ONE list, here
#: beside the vocabulary: the recorder's disk floor takes a reel at one of these before a reel that still owes a
#: survey, a read, a seal or a join, and the custody record calls a reap of any other station a reap before
#: extraction. EMPTY is reopenable (one survey's verdict), which is why it ranks a reel, never releases one.
READ_DONE = ("EMPTY", "CAPTURE", "ROUTED", "TOMBSTONE")

#: ⚠⚠ v2987 — HIS RULING, 2026-09-12, ON A SCREENSHOT OF HIS OWN SHELF: *"EMPTY and STATION aren't
#: river stages — remove it then.. it is confusing"*, and before that *"i want it down a river lane.
#: from top to bottom intake/WHATEVER IS REALLY FIRST and then tombstone at the bottom of it all"*.
#:
#: He was right that the screen was nonsense and wrong about the cause, which is why nothing is
#: removed here. EMPTY and STATION are REAL stages holding real reels (measured on his river the
#: same minute: EMPTY 0, STATION 6). What is wrong is that the SHELF PRINTS THE KEY. Every one of
#: these stations already carries its human name as the first word of its own OWES text, and SIX
#: OF NINE disagree with the key:
#:      INTAKE -> SURVEY · EMPTY -> ROUTE · STATION -> READ · PRINTER -> SEAL · ROUTED -> TOMBSTONE
#: and the key TOMBSTONE is the AFTER-state ("nothing — it is released, and the stamp is its
#: record"). So the section he reads as "TOMBSTONE · 0 · NEVER REACHED" is not the mouth of the
#: river at all — the mouth is the section labelled ROUTED, and it holds 20 of his reels.
#: Deleting two stations would have orphaned six reels and left the real defect in place.
#:
#: ⚠ ONE LIST, DERIVED, NOT A SECOND ONE TYPED OUT. The label is taken FROM `OWES` at import, so a
#: station whose description is reworded cannot drift from its own label — two hand-kept lists is
#: exactly the failure `STATIONS` itself is commented against. [[copy-drift]] [[label-outlived-referent]]
def _label_of(station, text):
    """The human stage name a station's own OWES text opens with. -> str

    Falls back to the KEY when the text does not open with a name, which is honest: a station
    nobody has described yet should read as its key rather than as a guess.
    """
    import re as _re
    m = _re.match(r"\s*([A-Z][A-Z \-]*[A-Z])\s*[\u2014-]", str(text or ""))
    return m.group(1).strip() if m else station


#: ⚠⚠ HIS NAMES WIN. Konyo, 2026-09-12, naming the stages on his own screen: *"for th elast oone
#: shows tombstone reads deleted.. and for shows station should read analyze for intake it should
#: read FRESH"*. Those three are HIS words and they are not negotiable against a derivation; the
#: rest fall back to the name each station's own OWES text already opens with.
#:
#: The river then reads, in lane order, exactly the way he asked for it — arrivals at the top and
#: the end of the journey at the bottom:
#:      FRESH · TRIAGE · ANALYZE · ROUTE   |  SEAL  |  CAPTURE · JOIN  |  TOMBSTONE · DELETED
#: ⚠ ROUTED IS THE REAL TOMBSTONE and the key TOMBSTONE is what follows it — the reels that have
#: LEFT THE DISK. That is why his screen showed "TOMBSTONE 0 NEVER REACHED" while 20 reels sat one
#: section above it under another name. [[label-outlived-referent]]
HIS_LABELS = {"INTAKE": "FRESH", "STATION": "ANALYZE", "TOMBSTONE": "DELETED"}


def labels():
    """Station key -> the name HE reads on the shelf. -> dict

    ⚠ ONE MAP, BUILT HERE. The shelf must never keep a second list of names: `STATIONS` already
    carries the comment about why two lists drift, and a label list is the same hazard wearing a
    friendlier word. [[copy-drift]]
    """
    return dict((st, HIS_LABELS.get(st) or _label_of(st, OWES.get(st))) for st in STATIONS)

#: ⚠ NOT a station in the list above, and deliberately so. UNKNOWN means the evidence could not be
#: read — never "nothing was found". It is reported beside the totals and never inside them, so a
#: shelf nobody could measure cannot be mistaken for a shelf with no work waiting.
UNKNOWN = "UNKNOWN"

#: what each station is waiting on. The gate, in his words, "placed accordingly".
OWES = {
    "INTAKE":    "SURVEY — nothing has classified this reel's frames yet",
    "TRIAGE":    "TRIAGE — the template is known and retro_triage has not walked its frames, so "
                 "whether it holds a panel at all is UNSURVEYED, not empty",
    "EMPTY":     "ROUTE — retro_triage walked it IN FULL and found ZERO panel frames, so there is "
                 "no item name in this footage and a paid read would buy nothing. ⚠⚠ THAT IS NOT "
                 "AN EXIT. His question, 2026-09-05: *\"this happens before it even enters the "
                 "printer and station? doesnt it need to be gated after also.\"* Right on both "
                 "counts. A reel with nothing to READ still has a door it came from and still "
                 "owes a stamped tombstone, so it continues down the same river carrying less "
                 "— it does not leave it. And the verdict is REOPENABLE: `panels` is what THIS "
                 "survey's classifier saw, `retro_triage.json` records no classifier version, so "
                 "EMPTY means 'nothing found by the survey of surveyedAt' and never 'nothing is "
                 "there'. (A9's 10-15% law: most footage is a farming run, and that is what "
                 "footage IS, not a fault.)",
    "STATION":   "READ — the survey walked it and found panels, and no item name has ever been "
                 "read from it. THIS is the paid queue.",
    "PRINTER":   "SEAL — the names were read; the session carries no seal to put them in",
    "JOIN":      "JOIN — sealed AND the names are on disk; the seal does not carry them. Code.",
    # ⚠⚠ v3020 — REG-340 WAS THE WRONG CITATION AND IT SENT HIM AT THE WRONG CAMERA.
    # This said "D2R prints the name only on the character panel, which the reel does not film".
    # REG-340 is about the CHARACTER name — the mule label — and the character panel carries a
    # name, a class and stats and NO ITEMS. These reels are missing ITEM names, which is a
    # different field with a different answer, and printer.py:461-465 already ruled the conflation:
    # "REG-340 is about the CHARACTER name on the character panel, this is about ITEM names, and
    # conflating the two left a recoverable gap looking permanent." extract_gap.py says the same,
    # and test_extract_gap_holding.test_not_a_holding_is_not_a_capture_verdict already guards it
    # at the verdict layer — so this string contradicted a law that was already passing.
    #
    # THE CAPTURE CHANGE THAT WOULD ACTUALLY HELP IS HOVER, NOT THE CHARACTER PANEL. An item's
    # name is printed in its TOOLTIP; hover_mode.py states the mechanic plainly — "a stash GRID
    # carries no names; only the tooltip does" — and MINI(AUTOMATIC) already walks each occupied
    # cell to render one. Filming the character panel would not unblock a single reel here.
    #
    # ⚠ AND IT IS PER-REEL, NOT ONE RULING. Measured 2026-09-12 over the nine reels then at this
    # station, panel frames were 0, 1, 1, 1, 1, 4, 6, 10, 10 — so "little was filmed" and "plenty
    # was filmed and the read yielded nothing" are both present and want different answers, the
    # second being a possible throttled read (REG the v1774 scar) rather than a camera problem.
    # [[label-outlived-referent]] [[unknown-stays-unknown]]
    "CAPTURE":   "CAPTURE, then ROUTE — sealed and the reader yielded no ITEM name. An item's "
                 "name lives in its TOOLTIP, and a grid carries none, so what is owed is HOVER "
                 "coverage (MINI AUTOMATIC) on a future session — not the character panel, which "
                 "answers REG-340's question about the mule and carries no items at all. ⚠ Read "
                 "it per reel: few panel frames means little was filmed; many panel frames with "
                 "no names may be a failed or throttled read, which is payable and retryable. "
                 "⚠ Also not an exit: it still owes a route and a stamped tombstone like every "
                 "other reel.",
    "ROUTED":    "TOMBSTONE — the extraction contract is satisfied; it may be released with a stamp",
    "TOMBSTONE": "nothing — it is released, and the stamp is its record",
}

#: ⚠⚠ THE FIELDS A STATION MAY BE DERIVED FROM. Anything outside this set is the keep-reason
#: wearing a disguise. `assert_independent_of_retention()` enforces it by walking THIS module's
#: own AST, because a rule that lives only in a docstring is a rule the next edit will not see.
#: ⚠⚠ v3378 — `extractSay` IS extract_gap's OWN FIVE-STATE VERDICT, forwarded rather than
#: re-derived. printer.py:508 has put it on every row as `stations.extract.say` since v2572 and
#: this module threw it away, then re-derived a cruder answer from `sealed AND names` — so the
#: river contradicted the engine it names as this station's authority. Measured on his shelf
#: 2026-09-20: 1 of 19 reels. It is EVIDENCE about what the reader found, never a keep-reason.
EVIDENCE_FIELDS = ("sealed", "names", "worthReading", "surveyed", "extractSay")

#: the fields that answer "why are we KEEPING these bytes". Reading any of them to decide a
#: station re-creates the exact defect. Named so the guard can fail on them by name.
RETENTION_FIELDS = ("tag", "funnel", "route", "held", "holdKind", "stage", "stageIdx")


def _captured_ms(reel, hist=None):
    """When this reel was actually filmed. -> (epoch_ms | None, source)

    ⚠⚠ THE FRAMES ARE THE CLOCK — NOT THE ID, AND NOT mtime. His correction, 2026-09-05:
    *"timestamps should be taken care of this though the 13 digit is like a reference id"*. He is
    right and the measurement shows it: `reel_s_1784984019250_95276`'s id says 1784984019250 while
    its FIRST FRAME says 1784984130673 — **111 seconds apart**. The id is stamped when the session
    opens; the frame is stamped when the picture was taken. Only one of those is the capture.

    So this reads `f_<epoch-ms>.jpg` and takes the EARLIEST, which is the recorder's own written
    evidence. `hover_calibration._frames_by_ts` already reads frame names this way, so this is the
    tree's existing convention rather than a second one.

    ⚠ mtime is not a candidate at all: a directory's mtime moves when anything TOUCHES it — a
    survey, a copy, a backup — so ordering by it would put a reel that was merely looked at ahead
    of one filmed months earlier. FIFO has to mean "filmed first".

    ⚠⚠ RETURNS None, NEVER 0, when no clock can be read. A zero is a date in 1970 and would sort
    to the FRONT of a FIFO queue — an unmeasured reel jumping ahead of every measured one, which
    is the failure mode this whole module exists to refuse. The `source` says which clock answered
    (`frames` / `id` / None) so a reel resting on the weaker one is visible rather than assumed.
    [[unknown-stays-unknown]]
    """
    d = os.path.join(hist or _hist_dir(), str(reel or ""))
    best = None
    try:
        # REG-1412 — the SAME listing the frame index and reel_retention._dir_mb walk (frame_ref.listing), so on
        # a console a still reel folder is read once, not once more per route() for every reel on the shelf
        import frame_ref as _fr
        _names = _fr.listing(d)
        if _names is None:
            raise OSError("the reel folder cannot be listed")
        for nm, _kind, _size in _names:
            if not nm.lower().endswith(".jpg"):
                continue
            digits = "".join(ch for ch in os.path.splitext(nm)[0] if ch.isdigit())
            if len(digits) < 13:
                continue
            try:
                ms = int(digits[-13:])
            except ValueError:
                continue
            if best is None or ms < best:
                best = ms
    except Exception:
        best = None
    if best is not None:
        return best, "frames"
    # ⚠ THE FALLBACK IS NAMED, NOT SILENT. A reel whose frames are gone (already pruned, or never
    # written) can still be ordered by its session id — but the caller must be able to see that it
    # is resting on the weaker clock, because the two differ by minutes and the id is an id.
    m = re.search(r"(\d{13})", str(reel or ""))
    if m:
        return int(m.group(1)), "id"
    return None, None


def _hist_dir():
    """Where the reels live. -> path"""
    return (os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist"))


def _station_of(ev):
    """The station this evidence puts a reel at. -> (station, why)

    ⚠ IT READS ONLY `EVIDENCE_FIELDS`. No retention tag, no keep-reason, no hold kind. If this
    function ever needs one of those to decide, the two questions have merged again and the guard
    below must fail rather than let it through.
    """
    if ev is None:
        return UNKNOWN, "the printer did not answer for this reel, so its position is unmeasured"
    sealed = ev.get("sealed")
    names = ev.get("names")
    surveyed = ev.get("surveyed")
    worth = ev.get("worthReading")
    # ⚠ None is not False for any of these. A reel whose survey could not be read is UNKNOWN, not
    # un-surveyed — the difference is the whole reason this module exists.
    if sealed is None or names is None:
        return UNKNOWN, ("sealed=%r names=%r — at least one is unmeasured, so no position can be "
                         "honestly assigned" % (sealed, names))
    if surveyed is False:
        return "INTAKE", "on the shelf and nothing has classified its frames"
    # ⚠ THE FURTHER-DOWN-RIVER STATES ARE TESTED FIRST. A reel that has already been read and
    # sealed is past the survey; asking whether it is worth reading would send it BACKWARDS.
    if sealed and names:
        return "JOIN", ("sealed and %d name(s) already read — the names exist and the seal does "
                        "not carry them" % int(names))
    if sealed and not names:
        return "CAPTURE", "sealed and the reader yielded no name at all"
    if names and not sealed:
        return "PRINTER", "%d name(s) read and the session carries no seal" % int(names)
    # ⚠⚠ NOT SEALED AND NO NAMES — and here the SURVEY decides the position, because the survey IS
    # a station on this river and not a flag beside it. His question, 2026-09-05: *"what decides
    # its worth reading or not why doesnt it go through the unified filtering process down the
    # river and through the station and printer."* It does: `worthReading` is
    # `retro_triage.worth_reading()`, which is `bool(panels)` from the full-frame triage pass.
    # My first cut flattened that verdict into a FLAG on one station, so 13 reels sat in a queue
    # of which only 7 could ever yield anything — the position said READ and the river had already
    # said otherwise for six of them. A river verdict belongs in the position.
    if worth is None:
        return "TRIAGE", ("the template is known and retro_triage has not walked its frames, so "
                          "whether it holds a panel is UNSURVEYED — which is not empty")
    if worth is False:
        return "EMPTY", ("retro_triage walked it IN FULL and found zero panel frames — there is "
                         "no item name in this footage, so there is nothing here to read")
    return "STATION", "the survey found panels and no name has ever been read from it"


#: ⚠⚠ v3378 — THE ONE THING A REEL AT `JOIN` MAY OWE THAT IS NOTHING. Kept OUT of `OWES` on
#: purpose: `OWES` is the map from STATION to standing gate and `_label_of` derives the shelf's
#: lane names from it, so a per-reel override living in there would invent a tenth lane.
NOTHING_OWED = ("NOTHING — sealed, the names WERE read, and not one of them can become a "
                "holding. No join is owed here and no footage is owed either.")


def _owes_of(station, ev):
    """What THIS reel owes at that station. -> (text, why)

    ⚠⚠ THE MODULE ALREADY PROMISED THIS AND THE CODE DID NOT DELIVER IT. `STATIONS` says, in its
    own comment: *"A reel's station is its POSITION; what it OWES is the named gate in front of
    it. Keeping those separate is the whole point — two reels can sit at the same position and
    owe different work, and one word for both is how `route` became the retention tag."* Then
    `route()` wrote `"owes": OWES.get(station)` — ONE string per station, handed to every reel
    standing there. A rule stated in a comment that the adjacent code does not implement is a
    rule nobody is keeping. [[measured-true-read-wrong]] [[plumbing-with-no-tap]]

    ⚠⚠ AND IT COST A REAL CONTRADICTION, MEASURED ON HIS SHELF 2026-09-20. Two reels sit at
    JOIN, and `extract_gap` — the engine `printer.py:508` names as this station's authority —
    gives them OPPOSITE verdicts on the same rows the router was reading:

        reel_s_1784984019250_95276   2 names, 1 with a container OPEN   -> RECOVERABLE
        reel_s_1786385768689_67392  45 names, every one on a Chronicle  -> NOT_A_HOLDING
            its own why: "Nothing is owed here: it is neither a join nor a capture gap."

    The router threw `say` away, re-derived `sealed AND names -> JOIN`, and handed the second
    reel the text "the seal does not carry them. Code." — 45 names filed as owed work against
    a law (v2772 `holding_possible`) that had already measured they can never be a holding: a
    Chronicle page is a checklist of items he mostly does not own, no container is open, so the
    contract's `location` has nothing to take. [[the-unjoined-end]] [[copy-drift]]

    ⚠ THE ASYMMETRY IS DELIBERATE AND IS THE SAFETY. Only the EXPLICIT `NOT_A_HOLDING` may
    downgrade the owed work to nothing. An unreadable verdict, an unrecognised word, a reel the
    engine could not answer for — every one of those keeps the station's standing text, because
    the direction that costs something is claiming nothing is owed when nobody could tell.
    [[unknown-stays-unknown]]

    ⚠ THIS MOVES NO REEL AND RELEASES NO FOOTAGE. The station is unchanged, `counts` is
    unchanged, and `seal_releases_frames` is not consulted here at all — the only thing that
    changes is the sentence describing what is waiting, which is the thing that was wrong.
    """
    base = OWES.get(station)
    if station != "JOIN":
        return base, ""
    say = (ev or {}).get("extractSay") if isinstance(ev, dict) else None
    if say is None:
        return base, ("extract_gap did not answer for this reel, so whether a join is owed is "
                      "UNKNOWN — the station's standing text stands rather than a guess")
    if say == "NOT_A_HOLDING":
        return NOTHING_OWED, ("extract_gap ruled NOT_A_HOLDING for this reel: the names were "
                              "read and none of them can satisfy the contract's `location`, so "
                              "there is no join to write. Forwarded from the engine, not "
                              "re-derived here")
    if say == "JOINED":
        return NOTHING_OWED, ("extract_gap ruled JOINED for this reel: the seal certifies name, location and "
                              "provenance, so the join is already written (REG-2004). Forwarded from the "
                              "engine, not re-derived here")
    if say == "RECOVERABLE":
        return base, ("extract_gap ruled RECOVERABLE for this reel — the names exist, a cell box "
                      "exists for them, and the seal carries neither. The join IS owed")
    return base, ("extract_gap answered %r, which is not a verdict this station knows how to "
                  "downgrade, so the standing gate stands" % (say,))


def _evidence(hist=None):
    """Per-reel evidence from the printer's own walk. -> (dict reel -> ev, why)

    ⚠⚠ `hist` IS ACCEPTED AND CANNOT BE HONOURED, AND SAYING SO IS THE POINT. `printer.stream()`
    takes only `(reel=None)` — it reads whatever shelf its own module resolves. So a caller doing
    `route(hist=<fixture>)` would take CAPTURE CLOCKS from the fixture and STATION EVIDENCE from
    the live shelf, and a fixture test would silently grade his real 40 reels and pass. Two
    independent audits caught this within minutes of each other.
    Rather than accept a parameter that quietly lies, this REFUSES a mismatched `hist` and names
    the supported route: point TV_HIST at the fixture (the tree's own convention), or patch
    `_evidence`. [[feedback-fixtures-never-touch-live-data]] [[plumbing-with-no-tap]]

    ⚠ THE PRINTER IS THE SOURCE and this does not re-derive it. `printer.stream()` already walks
    every reel; building a second walk here would be a second authority on the same question, and
    two authorities disagreeing about "where is this reel" is the defect one station up.
    """
    if hist and os.path.abspath(hist) != os.path.abspath(_hist_dir()):
        return None, ("refusing to mix shelves: hist=%r was passed, but printer.stream() reads "
                      "%r and takes no shelf argument. Set TV_HIST instead, or patch _evidence — "
                      "answering anyway would join this fixture's clocks to the live shelf's "
                      "evidence." % (hist, _hist_dir()))
    try:
        import printer
    except Exception as exc:
        return None, "printer would not import (%s)" % type(exc).__name__
    try:
        rep = printer.stream()
    except Exception as exc:
        return None, "printer.stream() raised (%s)" % type(exc).__name__
    if not rep.get("ok"):
        return None, "printer.stream() could not answer: %s" % str(rep.get("why") or "")[:160]
    # ⚠ WHEN the survey ran, read through retro_triage's own load() and never its file. EMPTY is
    # the verdict of ONE survey at ONE time, and `retro_triage.json` records no classifier
    # version — so without this the report cannot distinguish "nothing is there" from "nothing
    # was found by whatever the classifier was that day". [[stale-reading]]
    # ⚠ `seen_at is None` means THE SURVEY TIMES COULD NOT BE READ — it is not an empty survey.
    # This handler used to hand back `{}` on both the exception and the not-ok path, so every reel
    # then reported `surveyedAt: None` as though the store had been read and held nothing for it.
    # That collapses precisely the distinction the comment above says this exists to preserve.
    seen_at, seen_why = {}, ""
    try:
        import retro_triage as _rt
        blob, ok = _rt.load()
        if ok:
            for k, v in (blob or {}).items():
                seen_at[str(k)] = (v or {}).get("ts")
        else:
            seen_at = None
            seen_why = ("retro_triage.load() reported not-ok, so no survey time could be read for "
                        "any reel — surveyedAt is UNKNOWN, not absent")
    except Exception as exc:
        seen_at = None
        seen_why = ("the retro_triage store would not load (%s) — surveyedAt is UNKNOWN, not "
                    "absent" % type(exc).__name__)
    out = {}
    for row in (rep.get("rows") or []):
        st = row.get("stations") or {}
        ex = st.get("extract") or {}
        tp = st.get("template") or {}
        n = ex.get("names")
        out[str(row.get("reel") or "")] = {
            "sealed": ex.get("sealed"),
            "names": None if n is None else int(n),
            "worthReading": tp.get("worthReading"),
            # ⚠ extract_gap's verdict, PASSED THROUGH. None stays None: a station whose engine
            # could not be asked is UNKNOWN about what is owed, never "nothing is owed".
            "extractSay": ex.get("say"),
            # a reel the template station could not classify was never surveyed. `say` absent is
            # UNKNOWN-shaped and is passed through as None rather than turned into False.
            "surveyed": None if tp.get("say") is None else True,
            # None here has TWO causes and the report's `why` is what separates them: the store was
            # read and holds no time for this reel, or the store could not be read at all.
            "surveyedAt": None if seen_at is None else seen_at.get(str(row.get("reel") or "")),
        }
    return out, seen_why


def _routed_by_a_lane(path=None):
    """Reels an ACTING lane has closed out. -> (dict reel -> row | None, why)

    ⚠⚠ ACTOR ROWS ONLY, AND THAT IS WHAT STOPS THE RIVER FLAPPING. Routing changes no evidence, so
    `_station_of` goes on deriving EMPTY for a routed reel for ever. If this read observer rows too,
    the observer walk's own output would feed back in here, the station would oscillate
    EMPTY -> ROUTED -> EMPTY, and every walk would write another transition row into an append-only
    store. `river_stamp.run()` hard-codes `byKind: "observer"` with no way to say otherwise, so
    filtering to actors means this overlay is driven purely by lanes that ACTED and never by itself.

    ⚠ THE LAST ACTOR ROW WINS, not the first match. The store is append-only and ordered, so a reel
    that was routed and later re-opened by another acting lane must come back out of this set — a
    first-match read would pin it at ROUTED permanently and no lane could ever undo it.

    ⚠ TOMBSTONE IS NOT OVERLAID HERE, deliberately. Only the deleter writes that row, and a deleted
    reel is absent from `_evidence` entirely — an overlay for it would be a branch nothing can
    reach. [[plumbing-with-no-tap]]
    """
    try:
        import river_stamp as _st
    except Exception as exc:
        return None, ("the stamp store could not be imported (%s), so whether any reel has been "
                      "routed is UNKNOWN — it is NOT 'none have'" % type(exc).__name__)
    try:
        rep = _st.rows(path)
    except Exception as exc:
        return None, ("the stamp store raised %s, so whether any reel has been routed is UNKNOWN"
                      % type(exc).__name__)
    if not rep.get("ok"):
        return None, ("the stamp store could not be read (%s), so whether any reel has been routed "
                      "is UNKNOWN — it is NOT 'none have'" % (rep.get("why") or "no reason given"))
    last = {}
    for row in (rep.get("rows") or []):
        if row.get("byKind") != "actor":
            continue
        reel = row.get("reel")
        if reel:
            last[reel] = row
    return {k: v for k, v in last.items() if v.get("station") == "ROUTED"}, ""


def unreached_stations(counts, closed_n):
    """Which declared stations nothing reaches. -> [station]

    A pure function on purpose: route()'s full walk needs a working printer, an evidence store and
    real footage, so a gate that could only assert this through route() could only run on his
    machine — and Heart 2.0 correctly calls such a law UNPROVABLE. The RULE is separable from the
    WALK, so it is separated, and both the router and its gate exercise this same code.

    TOMBSTONE is the exception with a reason: it is reached by the closure LEDGER, a source this
    walk does not own. Every genuinely empty station still says so — silencing a real emptiness
    would trade one lie for another. [[gate-blind-to-unexercised-input]]
    """
    counts = counts or {}
    n = int(closed_n or 0)
    return [st for st in STATIONS
            if counts.get(st, 0) == 0 and not (st == "TOMBSTONE" and n > 0)]


def _closed_rows():
    """Every reel the closure ledger names, as ROWS. -> (list | None, why)

    ⚠⚠ THE ONE READER. `_closed_ledger()` is a census OVER this and `roster()` is a work-list over
    it; neither opens the file itself. Two readers of one ledger is how the counts in this family
    drift apart — the exact shape #36 was raised about, where three independent walks agreed at 41
    by luck and nothing enforced it. [[copy-drift]]

    Read through reel_retention's own path authority rather than a second os.path.join, so an
    isolated world resolves the same file the writer used.

    ⚠ None is UNKNOWN — "I could not tell what closed" — and is NEVER an empty list. An ABSENT
    ledger is different again and honestly returns `[]`: nothing has ever been tombstoned here.
    [[unknown-stays-unknown]]
    """
    try:
        import json as _json
        import reel_retention as _rr
        p = _rr._tombstone_path()
        with open(p, encoding="utf-8") as fh:
            d = _json.load(fh)
        reels = (d or {}).get("reels")
        if isinstance(reels, dict):
            reels = list(reels.values())
        if not isinstance(reels, list):
            return None, "the closure ledger has no `reels` collection"
        return [r for r in reels if isinstance(r, dict)], ""
    except FileNotFoundError:
        return [], "no closure ledger yet — nothing has ever been tombstoned here"
    except Exception as e:
        return None, "the closure ledger could not be read (%s)" % type(e).__name__


def _closed_ledger():
    """The reels that actually closed out. -> {"n", "why", "readable"}

    A census over `_closed_rows()`, which is the only thing in this module that opens the ledger.
    A ledger that cannot be read is UNKNOWN — `readable` False with n None — never a confident 0,
    because "nothing has closed" and "I could not tell what closed" are opposite facts and only
    one of them is good news. [[unknown-stays-unknown]]
    """
    rows, why = _closed_rows()
    if rows is None:
        return {"n": None, "readable": False, "why": why or "the closure ledger could not be read"}
    if not rows:
        return {"n": 0, "readable": True,
                "why": why or "the closure ledger names no reels — nothing has closed out here"}
    return {"n": len(rows), "readable": True,
            "why": "%d reel(s) have closed out and left the disk; they are not in the walk "
                   "above, which only sees what is still present" % len(rows)}


def route(hist=None, path=None):
    """Every reel on the shelf, with exactly one station each. -> dict

    The invariant is asserted, not assumed: `sum(counts.values()) == shelf` and every reel appears
    exactly once. A router that quietly drops a reel is the gap this was built to close.
    """
    ev, why = _evidence(hist)
    rep = {"ok": False, "stations": list(STATIONS), "owes": dict(OWES),
           "reels": [], "counts": {}, "unknown": 0, "shelf": 0, "why": why}
    if ev is None:
        import unknown_shelf as _us
        rep["why"] = _us.not_an_empty_shelf(why, "the walk did not answer and said nothing")
        # ⚠ v2817 — THE CLOSURE COUNT DOES NOT DEPEND ON THE WALK, so it is published here too.
        # The first cut attached `closed` only to the success path, and a consumer that asked
        # "what has closed out?" while the walk was UNKNOWN got no key at all — which reads as
        # "nothing", the exact conflation this whole change exists to end. The ledger is a
        # separate source; an unreadable WALK says nothing about it either way.
        rep["closed"] = _closed_ledger()
        rep["unreached"] = unreached_stations({}, (rep["closed"] or {}).get("n"))
        # ⚠⚠ v2881 — THE OUTLET IS A SEPARATE SOURCE TOO, AND IT WAS LEFT BEHIND.
        # The v2817 note directly above states the principle — "an unreadable WALK says nothing
        # about it either way" — and applied it to `closed`/`unreached` only. The stamp store is
        # the same shape: whether it could be READ has nothing to do with whether the shelf holds
        # reels, so a consumer asking "was the outlet readable?" on an empty shelf got None and ''
        # — no key at all, which reads as "no" for a store that answered perfectly.
        # MEASURED on CI (a runner has no reels, so every walk is UNKNOWN there): two laws in
        # test_the_river_has_an_outlet.py stub a READABLE store and still fail with "None is not
        # true" and "nothing says WHY the outlet could not be read". Both pass on his Mac, which
        # has a shelf — the host machine was the fixture. [[feedback-blind-fixture-green-gate]]
        # [[unknown-stays-unknown]] [[feedback-generalize-fixes]]
        _r, _ow = _routed_by_a_lane(path)
        rep["outletReadable"] = _r is not None
        rep["outletWhy"] = _ow
        return rep
    # ⚠⚠ v2770 — `path` IS THREADED, and it was not. Found by the post-ship review: route()
    # called the overlay with NO path, so the helper's own `path` parameter was unreachable and
    # `reel_route_lane.apply(by, path=X)` planned against the DEFAULT store while stamping into
    # X — reels already routed in X re-stamped, reels routed in the real store wrongly skipped.
    # A fixture run reading his production ledger to decide what to write into the fixture is
    # exactly what `_evidence`'s own hist refusal exists to prevent.
    # [[feedback-fixtures-never-touch-live-data]]
    routed, outlet_why = _routed_by_a_lane(path)
    # REG-3329 (#44 - the river on every PC). MEASURED 11-07 on his Mac: route() stationed 42 reels while the shelf
    # (reel_story) held 30, and the console's invariant router-and-shelf-agree read the gap as a fault. All 12 extra
    # were EVIDENCE REMNANTS - reels the drain already released and tombstoned WITH a `kept` list, whose cited pictures
    # stayed (his section 26); the folder lives on only for those pictures. The walk saw a folder and stationed each as a
    # live reel: 8 UNKNOWN (nothing measurable is left) and 4 ROUTED "owes only a tombstone" - a tombstone they already
    # have, so the river's stuck counts carried work that was done. A remnant is not a reel on the shelf: retention's own
    # rule (reel_retention.remnant_reels - the ONE authority; a tombstone-ledger record, never a keep tag) is asked here,
    # and each remnant is NAMED in `remnants`, never silently dropped. Unreadable -> nothing is set apart (as before).
    try:
        import reel_retention as _rrem
        _rem = set(_rrem.remnant_reels(_hist_dir()) or ())
    except Exception:
        _rem = set()
    rep["remnants"] = sorted(r for r in ev if r in _rem)
    rows = []
    for reel, e in ev.items():
        if reel in _rem:
            continue
        station, swhy = _station_of(e)
        # ⚠⚠ THE OUTLET. Everything above derives a READ-FATE from the footage; this is the one
        # thing that is not derivable from it. Routing is an ACT — a lane decided the extraction
        # contract was satisfied and closed the reel out — and no amount of looking at frames will
        # ever show it. So it is overlaid here rather than inside `_station_of`, which stays a pure
        # function of EVIDENCE_FIELDS and is held to that by `assert_independent_of_retention()`.
        #
        # This is what unwelds ROUTED from the deleter. `river_walk`'s own note said the only
        # writer of a tombstone row lives inside `reel_retention.apply_plan`, so a reel could not
        # be recorded as finished without being REMOVED, and removal is behind the arming lock —
        # which is why this station read 0 for its whole existence. Finishing and deleting are two
        # different facts about a reel, and only the second one is locked.
        _r = (routed or {}).get(reel)
        if _r is not None:
            station = "ROUTED"
            swhy = str(_r.get("why") or ("closed out by %s" % (_r.get("by") or "an unnamed lane")))
        ms, src = _captured_ms(reel, hist)
        # ⚠⚠ `e` MAY BE None, AND THIS LINE USED TO CRASH ON IT — found 2026-09-05 by the very
        # sabotage that replaced `reel.route`'s REG-600 axis, on its first real run. `_station_of`
        # opens with `if ev is None: return UNKNOWN, "the printer did not answer for this reel"` —
        # a branch written on purpose, documented, and UNREACHABLE THROUGH ITS ONLY CALLER, which
        # went straight on to `e.get("sealed")` and raised AttributeError. So the module's whole
        # UNKNOWN story ended in a traceback the moment a reel actually went unanswered.
        # The old axis compared two module constants and could never have found it.
        # [[the-unjoined-end]] [[unknown-stays-unknown]]
        _e = e if isinstance(e, dict) else {}
        # ⚠ AFTER the outlet overlay above, never before: a reel the overlay moved to ROUTED owes
        # what ROUTED owes, and asking on the pre-overlay station would print the old gate.
        _owes, _owes_why = _owes_of(station, _e)
        row = {
            "reel": reel,
            "station": station,
            "why": swhy,
            "owes": _owes,
            # ⚠ the REASON the owed work is what it is, beside it and never instead of it. A row
            # that reads NOTHING with no citation is indistinguishable from a row nobody asked
            # about. [[zero-needs-a-denominator]]
            "owesWhy": _owes_why,
            "capturedMs": ms,
            "clockFrom": src,
            "sealed": _e.get("sealed"),
            "names": _e.get("names"),
            "worthReading": _e.get("worthReading"),
            # the engine's own verdict, on the row, so a reader can check the owed work against
            # it rather than taking this module's word for it
            "extractSay": _e.get("extractSay"),
            "surveyedAt": _e.get("surveyedAt"),
        }
        if station == "ROUTED":
            # the act that closed it out, beside the station. Named closedOut, never "route": that word is a retention
            # field, and assert_independent_of_retention refuses it in route(). An empty from is unknown, not a guess.
            if isinstance(_r, dict):
                row["closedOut"] = {"from": _r.get("from") or None, "by": _r.get("by") or None, "why": swhy}
            else:
                row["closedOut"] = None
        rows.append(row)
    # FIFO: oldest capture first. ⚠ A reel with NO readable clock sorts LAST, never first — None
    # must not be coerced to 0, because 0 is 1970 and would put every unmeasured reel at the head
    # of the queue ahead of reels whose age is actually known.
    rows.sort(key=lambda r: (r["capturedMs"] is None, r["capturedMs"] or 0, r["reel"]))
    counts = {s: 0 for s in STATIONS}
    unknown = 0
    for r in rows:
        if r["station"] == UNKNOWN:
            unknown += 1
        else:
            counts[r["station"]] += 1
    # ⚠⚠ `why` IS NOT BLANKED ON SUCCESS — v2658's `seen_why` DIED HERE, one line after it was
    # written. `_evidence()` was taught to return a reason when the retro_triage store could not
    # be read, and its own comment says *"None here has TWO causes and the report's `why` is what
    # separates them."* Then this line overwrote it with "". Measured with
    # `retro_triage.load -> ({}, False)`: `ok=True shelf=40 why='' surveyedAt=[None, None, None]`
    # — an unreadable survey store indistinguishable from "read, and holds no time for this reel",
    # which is the exact collapse the change was written to prevent.
    # Caught by a same-family review of the PUSHED bytes; the fix and its defeat shipped together.
    # [[the-unjoined-end]] — two halves each written correctly, never joined.
    #
    # A successful walk with an unreadable survey is a REAL partial: the stations are known, the
    # survey times are not. So `why` carries that, and `surveyedAtWhy` names it as a field a
    # consumer can branch on rather than a sentence it must parse. [[unknown-stays-unknown]]
    rep.update({"ok": True, "reels": rows, "counts": counts, "unknown": unknown,
                "shelf": len(rows), "why": why or ""})
    rep["surveyedAtWhy"] = why or ""
    # ⚠ THE GAP CHECK, and it is the reason this returns a report rather than a list. `counts`
    # excludes UNKNOWN on purpose, so the sum only reconciles when UNKNOWN is added back — which
    # forces any caller printing a total to say how many it could not place.
    rep["reconciles"] = (sum(counts.values()) + unknown) == len(rows)
    # ⚠⚠ POSITION IS NOT THE SAME AS THE BILL, and reporting one number would hide that. 13 reels
    # sit at STATION; the survey says only 7 are WORTH reading. A paid queue built from the
    # position alone would buy six reads the survey already argued against — which is the
    # 2026-08-28 incident's shape exactly. Both numbers are published; neither is folded.
    rep["readable"] = sum(1 for r in rows
                          if r["station"] == "STATION" and r["worthReading"] is True)
    rep["notWorth"] = sum(1 for r in rows
                          if r["station"] == "STATION" and r["worthReading"] is False)
    rep["worthUnknown"] = sum(1 for r in rows
                              if r["station"] == "STATION" and r["worthReading"] is None)
    # ⚠⚠ NAME THE STATIONS NOTHING REACHES, because this module's whole case against
    # `reel_story` was that four of its six stages were permanently empty and nothing said so.
    # A router that silently publishes zeros for its own far end has reproduced the defect it was
    # built to expose. ROUTED and TOMBSTONE are unreached TODAY — nothing routes or tombstones
    # yet (that is gh #210) — and this says so rather than letting a 0 read as "none waiting".
    # ⚠⚠ v2817 (#36) — TOMBSTONE WAS A DECLARED STATION NO CODE PATH COULD EVER ASSIGN.
    # MEASURED 2026-09-09: STATIONS declares TOMBSTONE, nothing in _station_of()/route() assigns
    # it, counts["TOMBSTONE"] is structurally 0, and `unreached` named it EVERY RUN — the module
    # reporting its own gap to nobody. Meanwhile tv/reel_tombstones.json held 428 closed-out
    # reels with ZERO overlap with the 41 on disk. So river_lanes' TOMBSTONE lane ("closed out —
    # the extraction contract is satisfied") could only ever show ROUTED-but-still-present reels:
    # it could never show a reel that had actually closed out, which is its entire purpose.
    #
    # ★ THE PER-REEL WALK IS NOT WIDENED, AND THAT IS DELIBERATE. Every source feeding this router
    # walks what is on disk; a reel whose directory is gone has no row to derive. Folding 428
    # ledger entries into `rows` would silently change `shelf` from 41 to 469 — a count he reads,
    # moved by a refactor. The closure ledger is published BESIDE the walk, with its own
    # denominator and its own source named, so the lane can show what closed without any number
    # quietly meaning something new. [[label-outlived-referent]] [[zero-needs-a-denominator]]
    rep["closed"] = _closed_ledger()
    # A station backed by 428 records is not "unreached" — it is reached by a source this walk
    # does not own. Anything genuinely empty still says so.
    rep["unreached"] = unreached_stations(counts, (rep["closed"] or {}).get("n"))
    # ⚠⚠ AN UNREADABLE STAMP STORE MUST NOT RENDER AS "NOTHING IS ROUTED". `_routed_by_a_lane`
    # returns None when it could not read, and the loop above then derives every reel — producing
    # a confident ROUTED 0 that is actually UNKNOWN. This is the field that separates them, and
    # `outletReadable` is a boolean a consumer can branch on rather than a sentence it must parse.
    # [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    rep["outletReadable"] = routed is not None
    rep["outletWhy"] = outlet_why
    return rep



def roster(hist=None, path=None, rep=None):
    """ONE work-list spanning a reel's WHOLE LIFE — arrival to closure. -> dict

    -> {"ok", "rows", "onDisk", "closed", "both", "lifetime", "closedReadable", "why", ...}

    ⚠⚠ WHY THIS EXISTS, MEASURED 2026-09-09 (#36). Every source feeding `route()` walks what is
    CURRENTLY ON DISK. The moment `reel_retention.apply_plan()` removes a reel's directory that
    reel is written into the closure ledger and vanishes from every list this family touches. On
    his shelf that day: 41 reels in the per-reel walk, 428 in the ledger, ZERO overlap — so the
    per-reel surfaces covered 41 of 469 lifetimes, **8.7%**, and the other 91.3% were visible only
    as one aggregate sentence attached to rows about other reels. A number a reader has to regex
    off an unrelated row is a number nothing can join to.

    ★ THIS DOES NOT WIDEN `route()`, AND THAT IS THE POINT. `route()["shelf"]` still means "reels
    on disk" and still reconciles against its own counts. Folding 428 ledger entries into that
    walk would move a number he reads — 41 becomes 469 — with no line on any screen saying why.
    So the union lives HERE, with every part carrying its own denominator and its own named
    source, and a caller must ask for a lifetime view by name rather than receiving one by
    accident. [[label-outlived-referent]] [[zero-needs-a-denominator]]

    ⚠⚠ THE STATION `TOMBSTONE` IS ASSIGNED HERE AND NOWHERE ELSE, which is what finally makes it
    reachable. `STATIONS` has declared it since the module was written and no code path in
    `_station_of()` or `route()` could ever produce it — `route()["unreached"]` named it EVERY
    RUN, the module reporting its own gap to nobody. A declared vocabulary word nothing can assign
    is a label that outlived its referent. [[label-outlived-referent]] [[plumbing-with-no-tap]]

    ⚠ AN UNREADABLE LEDGER IS `closed: None`, NEVER 0, and `lifetime` is then None too — a total
    over a half-read union is a fabricated number. The rows that WERE read are still returned, so
    a partial answer stays useful without pretending to be whole. [[unknown-stays-unknown]]

    ⚠ A REEL IN BOTH HALVES IS A CONTRADICTION, NOT A DUPLICATE. It is on disk AND recorded as
    deleted; one of the two records is wrong. It appears ONCE, as its live row, flagged
    `alsoClosed`, and it is named in `both` so the total cannot be inflated by counting it twice.
    Zero overlap today is luck — nothing enforces it — which is exactly the complaint that opened
    this work.
    """
    # ⚠ `rep` IS ACCEPTED SO A CALLER THAT ALREADY WALKED DOES NOT WALK TWICE. `river_lanes`
    # draws both halves from one answer; without this it would pay for a second full `route()`
    # (0.2s of printer + evidence + footage) on a surface his console polls, and the two walks
    # could disagree about the same shelf a second apart. One reading, shared.
    rep = route(hist, path) if rep is None else rep
    out = {"ok": False, "rows": [], "onDisk": None, "closed": None, "both": [],
           "lifetime": None, "closedReadable": False, "walkReadable": bool(rep.get("ok")),
           "stations": list(STATIONS), "why": ""}
    closed_rows, closed_why = _closed_rows()
    out["closedReadable"] = closed_rows is not None
    out["closedWhy"] = closed_why

    live = list(rep.get("reels") or []) if rep.get("ok") else []
    if not rep.get("ok"):
        out["why"] = ("the on-disk walk is UNKNOWN — %s"
                      % (rep.get("why") or "no reason given"))
    else:
        out["onDisk"] = len(live)

    live_names = {str(r.get("reel") or "") for r in live}
    both = []
    rows = []
    for r in live:
        row = dict(r)
        row["onDisk"] = True
        row["closedMs"] = None
        rows.append(row)

    if closed_rows is not None:
        seen = {}
        for t in closed_rows:
            nm = str(t.get("reel") or "")
            sid = str(t.get("session") or "")
            if not nm and sid:
                nm = "reel_" + sid
            if not nm:
                continue
            # the ledger has keyed by reel dir name and by bare session id across versions; a row
            # matching a live reel under EITHER key is the contradiction, not two reels.
            alias = ("reel_" + sid) if sid and not sid.startswith("reel_") else nm
            if nm in live_names or alias in live_names:
                both.append(nm)
                for row in rows:
                    if row.get("reel") in (nm, alias):
                        row["alsoClosed"] = True
                        row["closedMs"] = t.get("deletedTs")
                continue
            if nm in seen:
                continue
            seen[nm] = True
            _st = t.get("startedTs")
            rows.append({
                "reel": nm,
                "station": "TOMBSTONE",
                "why": str(t.get("why") or "closed out; the ledger records no reason"),
                "owes": OWES.get("TOMBSTONE"),
                # ⚠ SAME CLOCK RULE AS THE LIVE WALK: the capture time, None when unrecorded, and
                # None must not become 0 — 0 is 1970 and would sort every unmeasured reel to the
                # head of a FIFO queue ahead of reels whose age is actually known.
                "capturedMs": (int(_st) if isinstance(_st, (int, float)) else None),
                "clockFrom": ("tombstone.startedTs" if isinstance(_st, (int, float))
                              else "none — the ledger recorded no capture time"),
                "closedMs": t.get("deletedTs"),
                "onDisk": False,
                "mb": t.get("mb"),
                "frames": t.get("frames"),
                "pages": t.get("pages"),
                "focus": t.get("focus"),
                # the evidence fields are UNREADABLE, not absent: the footage they were derived
                # from is gone, so None here means "cannot be re-derived", never "was false".
                "sealed": None, "names": None, "worthReading": None, "surveyedAt": None,
            })
        out["closed"] = len(seen)

    # FIFO inherited, one rule, applied once over the union. Identical key to `route()`'s.
    rows.sort(key=lambda r: (r.get("capturedMs") is None, r.get("capturedMs") or 0,
                             str(r.get("reel") or "")))
    out["rows"] = rows
    out["both"] = sorted(set(both))
    if out["onDisk"] is not None and out["closed"] is not None:
        out["lifetime"] = out["onDisk"] + out["closed"]
    counts = {}
    for r in rows:
        counts[str(r.get("station"))] = counts.get(str(r.get("station")), 0) + 1
    out["counts"] = counts
    out["ok"] = bool(rep.get("ok")) and closed_rows is not None
    # ⚠ `reconciles` OVER THE UNION, published rather than assumed — same discipline as `route()`.
    out["reconciles"] = (out["lifetime"] is not None and len(rows) == out["lifetime"])
    if out["ok"]:
        out["why"] = ("%d reel lifetime(s): %d still on disk and walkable, %d closed out and "
                      "readable only from the ledger%s"
                      % (out["lifetime"], out["onDisk"], out["closed"],
                         (" · %d reel(s) are in BOTH records, which is a contradiction: %s"
                          % (len(out["both"]), ", ".join(out["both"][:4]))) if out["both"] else ""))
    elif closed_rows is None:
        out["why"] = ((out["why"] + " · ") if out["why"] else "") + \
                     ("the closure ledger is UNKNOWN (%s), so the lifetime total is UNKNOWN — "
                      "NOT the %d on disk" % (closed_why or "no reason given",
                                              out["onDisk"] if out["onDisk"] is not None else -1))
    return out


def owed(station="STATION", hist=None, limit=None, worth_only=False):
    """The reels waiting at one station, OLDEST FIRST. -> (list, why)

    ⚠⚠ THIS IS A QUEUE, NOT AN INSTRUCTION. Nothing in this module consumes it. Wiring a paid
    reader to `owed("STATION")` would start a sweep per reel on HIS money, and that is his call
    to make with the number in front of him — 2026-08-28 is the precedent: a predicate that read
    as equivalent queued 19 reels where retention said 2, three of them test fixtures.

    ⚠ `worth_only` defaults to FALSE on purpose, so the plain call answers "where is everything"
    rather than silently shrinking the shelf. A PAID caller must pass True and thereby say, at its
    own call site, that it is buying reads — the filter is never applied on its behalf.
    ⚠ True also drops `worthReading is None`: a survey that could not be read is not permission.
    """
    rep = route(hist)
    if not rep.get("ok"):
        return None, rep.get("why") or "the shelf could not be read"
    rows = [r for r in rep["reels"] if r["station"] == station]
    if worth_only:
        rows = [r for r in rows if r["worthReading"] is True]
    return (rows[:limit] if limit else rows), ""


def _string_keys_read_by(fn):
    """Every literal string key `fn` looks up, by AST. -> set

    ⚠⚠ AN AST WALK, NOT A GREP, AND THAT IS NOT PEDANTRY — three guards in this repo have been
    satisfied by their own comments, and one of them matched a comment I had just written about
    the very thing it was checking. Text search cannot tell a rule from a sentence describing the
    rule. [[source-reading-guard]]
    """
    import ast
    import inspect
    import textwrap
    # ⚠ dedent FIRST. `inspect.getsource` on a nested function returns it at its ORIGINAL
    # indentation, which `ast.parse` rejects outright with IndentationError — so the guard would
    # refuse every closure handed to it, including its own RED-proof cases. It fails closed rather
    # than green, which is the right direction, but a guard that cannot read its own subject is
    # measuring nothing. Caught by its own sabotage case. [[feedback-suspect-the-instrument]]
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    seen = set()
    for node in ast.walk(tree):
        # x.get("k") and x["k"] — both forms, because either would re-couple it
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "get" and node.args:
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                seen.add(a.value)
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                and isinstance(node.slice.value, str):
            seen.add(node.slice.value)
    return seen


def assert_independent_of_retention():
    """Prove the station is derived from evidence and nothing else. -> (ok, findings)

    ⚠⚠ IT CHECKS BOTH HALVES, because checking only the decider leaves the obvious hole open.
    `_station_of` could stay spotless while `_evidence` quietly copies the retention tag into the
    dict it is handed — the coupling would be back, one function upstream, and a guard aimed only
    at the decider would report clean. That is [[the-unjoined-end]] in reverse: two halves, and
    the guard watching one of them.
    """
    findings = []
    for fn, forbidden, what in (
        (_station_of, RETENTION_FIELDS,
         "decides the station"),
        (_evidence, ("funnel", "route", "tag", "held", "holdKind"),
         "builds the evidence the station is decided from"),
        # ⚠⚠ THE THIRD HALF, ADDED WITH THE OUTLET. This guard's own docstring warns that the
        # coupling could come back "one function upstream" — and the outlet overlay put a real
        # decision into `route()`, which was not being watched at all. A station now gets its final
        # value here, so this is exactly where a keep-reason would next try to enter. It reads an
        # ACTOR STAMP, which is a record of an act and not a retention tag; this holds it to that.
        (route, RETENTION_FIELDS,
         "overlays the outlet and settles the final station"),
        # ⚠⚠ v2770 — THE HELPER, TOO. Found by the post-ship review: `_string_keys_read_by` parses
        # only the named function's OWN source and does not recurse into callees, so adding
        # `route` above watched the composition point while the overlay's actual key reads —
        # row.get("byKind"), row.get("station") — sat unguarded one call down. An edit making the
        # overlay consult row.get("held") or row.get("tag") is the keep-reason re-entering "one
        # function upstream", which is the failure this guard's own docstring names, and it would
        # have passed green while the entry above claimed to cover exactly that place.
        (_routed_by_a_lane, RETENTION_FIELDS,
         "reads the actor rows the outlet overlay is driven by"),
        # ⚠⚠ v3378 — THE FOURTH HALF. `_string_keys_read_by` does not recurse into callees, so
        # `route`'s entry above watches the composition point while `_owes_of`'s own key reads sit
        # one call down — exactly the hole v2770 found for `_routed_by_a_lane` and closed the same
        # way. A per-reel owed-work text is a fresh place for a keep-reason to enter (`held` and
        # `holdKind` are precisely the words a future edit would reach for to explain a hold), and
        # unwatched it would pass green while the entry above claimed to cover it.
        (_owes_of, RETENTION_FIELDS,
         "decides what THIS reel owes at its station"),
    ):
        try:
            seen = _string_keys_read_by(fn)
        except Exception as exc:
            findings.append("the guard could not parse %s (%s) — that is a REFUSAL, never a pass"
                            % (fn.__name__, type(exc).__name__))
            continue
        if not seen:
            findings.append("the walk found NO string-key reads in %s, which %s. That is an "
                            "instrument failure, not a clean result — a guard that inspects "
                            "nothing reports clean forever. [[feedback-suspect-the-instrument]]"
                            % (fn.__name__, what))
        for f in sorted(seen):
            if f in forbidden:
                findings.append("%s reads %r — the KEEP-REASON reaching the read-fate, which is "
                                "the exact defect this module exists to undo" % (fn.__name__, f))
    return (not findings), findings


def main(argv):
    rep = route()
    print("\nA7·ROUTE — one station per reel, from the reel's own evidence\n")
    if not rep.get("ok"):
        print("  UNKNOWN — %s\n" % rep.get("why"))
        return 2
    for s in STATIONS:
        n = rep["counts"].get(s, 0)
        if n or "-v" in argv:
            print("  %-10s %3d   owes %s" % (s, n, OWES.get(s, "")[:78]))
    print("  %-10s %3d   %s" % (UNKNOWN, rep["unknown"],
                                "position unmeasured — never folded into a total"))
    print("\n  shelf %d · reconciles %s" % (rep["shelf"], rep["reconciles"]))
    if rep.get("unreached"):
        print("  UNREACHED (nothing is at these — a 0 here is not 'none waiting'): %s"
              % ", ".join(rep["unreached"]))
    print("  at STATION: %d worth reading · %d the survey argues against · %d survey unreadable"
          % (rep["readable"], rep["notWorth"], rep["worthUnknown"]))
    q, _ = owed("STATION", limit=5, worth_only=True)
    if q:
        print("\n  the READ queue, oldest first (nothing consumes it — a queue, not an arming):")
        for r in q:
            print("    %-34s captured=%d names=%s sealed=%s"
                  % (r["reel"][:34], r["capturedMs"], r["names"], r["sealed"]))
    ok, findings = assert_independent_of_retention()
    print("\n  independent of the keep-reason: %s" % ("YES" if ok else "NO"))
    for f in findings:
        print("    ✗ %s" % f)
    print()
    return 0 if (rep["reconciles"] and ok) else 1


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
