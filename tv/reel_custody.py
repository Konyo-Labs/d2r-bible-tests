#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE CUSTODY RECORD — one reel, every hand that held it, each answer QUOTED from the store that hand wrote.

His vision, 2026-09-28 (HANDOFF §30, task #55): *"think about it like a robot AI vacuum cleaner.. it maps out the
rooms and house and areas it cant go.. same here it needs to map everything out ... witnesses obviously like some
sort of stamping system"*. The item-level half of that (SPOT / TRAIL / CONTEXT, pictures that may LINK from day one
and NAME only once HARDENED, carried loot OWNED right away — his §31 rulings) is phases P1-P5 of
55_CHAIN_OF_CUSTODY_DESIGN.md and is NOT built here. This is the first slice underneath it: the REEL's chain of
custody, because an item's trail is stamped onto frames, frames live in reels, and today nothing can say in one
place who has held a reel.

⚠⚠ WHAT WAS MISSING, MEASURED 2026-09-29 ON HIS TREE (read-only). Five stores each hold ONE fragment of a reel's
custody, keyed three different ways, and nothing joins them:

    reel_tombstones.json   460 rows — EVERY ONE says "sealed by BOTH lanes"
    vault_swept.json        51 seals — only  44 of those 460 have one       (keyed s_<ms>_<n>)
    chronicle_swept.json   431 seals — 404 of the 460 have one              (keyed reel_s_<ms>_<n>)
    retro_triage.json      478 rows  — 445 of the 460 were surveyed         (keyed reel_s_<ms>_<n>)
    river_stamp.jsonl      169 rows  —  50 of the 460 were ever stamped, and 0 stamps say TOMBSTONE
    the shelf               33 reels — 33 stamped · 33 surveyed · 21 chronicle-sealed · 7 vault-sealed

    56 tombstones have NEITHER seal. The permanent record of an irreversible delete names two hands that the
    hands' own records say never touched the reel. `end_routes.derived_from` already counts that as a NUMBER
    (labelContradictions); no surface could show it PER REEL, beside the hands that did hold it.

So this module answers, for one reel, the robot-vacuum question at reel granularity — which rooms did it pass
through, which did it never enter, and which room's record contradicts another's:

    recorder   the shelf directory + the recorder's own reap/refusal records   (tv_diablo writes them)
    triage     retro_triage.json                                                (the FREE structural survey)
    printer    chronicle_swept.json + the reads the journal holds for it       (the chronicle sweep / reader)
    vault      vault_swept.json + the witness index                             (the vault sweep)
    tombstone  reel_tombstones.json + the deleter's CURRENT intent (the plan)   (reel_retention)

=== THE RULES, AND WHY EACH IS NOT NEGOTIABLE =========================================================

1. **EVERY ANSWER IS QUOTED FROM ITS OWNER. NOTHING IS RE-DERIVED.** The four dict stores are read ONCE through
   `end_routes.sources()` (which itself asks `retro_triage._store_path` and `reel_retention._tombstone_path`);
   the seal's meaning is `frame_authority.seal_verdict`; the journey is `river_stamp.history`; the lane at a
   station is `river_walk.LANE_OF_STATION`; who took a picture is `read_pictures.who_took`; the door a tombstoned
   reel left by is `end_routes.verdict`; the capture clock is `reel_router._captured_ms`; every lookup in a
   store keyed both ways is `reel_retention.lookup_either_way`. REG-563/564 were two modules hand-writing the
   same lookup with different precedence. [[copy-drift]] §1: one owner, everyone else quotes.

2. **A HAND IS `held: True | False | None`, AND THE THREE ARE THREE.** True = that hand's own store carries a
   record for this reel. False = the store was READ (present, or never written) and holds none — a measured
   absence, a room the vacuum never entered. None = the store exists and would not read, so whether that hand
   held the reel is UNKNOWN. Collapsing None into False is how "the vault never sealed it" gets said about a
   store nobody could open, and a contradiction is NEVER raised on a None side. [[unknown-stays-unknown]]

3. **A CONTRADICTION IS PUBLISHED WITH BOTH SIDES AND NEVER RESOLVED.** Two writers disagreeing about one reel
   is the finding: the deleter's sentence vs the seal stores, the ledger's "removed" vs a directory still on
   the shelf, a hand-stamped TOMBSTONE vs a ledger with no row. Each row names the left writer, the right
   writer and what each says. Averaging them, or trusting the louder one, would hide exactly what he asked
   this map to show. [[feedback-contradiction-is-the-finding]]

4. **THE JOURNEY IS THE RIVER'S, THE CUSTODY IS THE STORES'.** `river_stamp` remembers the stations a reel
   REACHED (position, dated); the hands here are what each store RECORDS. They can legitimately disagree —
   the river cannot stamp TOMBSTONE at all (river_stamp's own note: the deleter does not stamp) — so the two
   are published side by side under different names and never folded into one "status".

⛔ IT READS. IT WRITES NOTHING, DELETES NOTHING, ARMS NOTHING, SPENDS NOTHING. It is #253-honest: it reads THIS
PC's stores only, so the record it hands the console is this install's own custody, never the fleet's.

    python3 tv/reel_custody.py <reel>      # one reel's custody, every hand
    python3 tv/reel_custody.py             # the census — which hand holds each reel, and the contradictions
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: the hands, in custody order. The order IS the chain: a reel is recorded before it is surveyed, surveyed
#: before it is read, read before it is sealed, and sealed (or proven empty) before it is closed out.
HOLDERS = ("recorder", "triage", "printer", "vault", "tombstone")

#: who WRITES each hand's record — named so a contradiction row can say which writer said what
WRITER = {
    "recorder": "the recorder (tv_diablo: the reel directory, reel_reaps.jsonl, read_pictures.jsonl)",
    "triage": "retro_triage (retro_triage.json)",
    "printer": "the chronicle sweep (chronicle_swept.json) and the reader's journal",
    "vault": "the vault sweep (vault_swept.json) and frame_authority's witness index",
    "tombstone": "reel_retention (reel_tombstones.json)",
}

#: the sentence the deleter writes into EVERY tombstone (reel_retention.plan's single `eligible` branch).
#: Quoted here, not owned: end_routes.derived_from counts the same phrase for the same reason.
BOTH_LANES = "sealed by BOTH lanes"

#: the doctor's own three words, so the row hands them straight through
OK, MISSING, UNKNOWN = "ok", "missing", "unknown"


# ══ WHERE THE STORES ARE — every path is an owner's answer ═══════════════════════════════════════════════════

def world(hist=None, stamp_path=None):
    """Where each store this record reads lives. -> dict of name -> path

    ⚠ EACH PATH IS ASKED OF ITS OWNER, never joined here from a directory and a filename. The four dict stores
    come from `end_routes._store_paths` (which asks retro_triage and reel_retention for theirs); the stamp
    store from `river_stamp._store_path`; the recorder's records from `read_pictures.root_of`, which is the
    derivation tv_diablo._reap_record itself uses. A private copy of any of these rules is REG-563's class.
    With no `hist`, every owner honours TV_HIST on its own, so a harness that set it gets a fixture world
    without this module knowing. [[copy-drift]] [[feedback-fixtures-never-touch-live-data]]
    """
    import end_routes as _er
    import read_pictures as _rp
    import river_stamp as _rs
    try:
        import frame_authority as _fa
        h = _fa._hist_dir(hist)
    except Exception:
        # a fixture that named TV_HIST keeps its world even when frame_authority cannot load (never his live shelf)
        h = hist or (os.environ.get("TV_HIST") or "").strip() or os.path.join(HERE, "frames", "hist")
    er = _er._store_paths(hist)
    rec_root = _rp.root_of(h)
    out = {
        "hist": h,
        "retro_triage": er["retro_triage.json"],
        "chronicle_swept": er["chronicle_swept.json"],
        "vault_swept": er["vault_swept.json"],
        "reel_tombstones": er["reel_tombstones.json"],
        "river_stamp": stamp_path or _rs._store_path(None),
        "reel_reaps": os.path.join(rec_root, _rp.REAPS),
        "read_pictures": os.path.join(rec_root, _rp.REFUSALS),
        # ⚠ the durable stores (vault_accum, vault_seen) live BESIDE the vault seal store: tv/ on his console
        # and the fixture root under TV_HIST — frame_authority reads all three from one root.
        "witness_root": os.path.dirname(er["vault_swept.json"]),
    }
    return out


def sources(hist=None, stamp_path=None, w=None):
    """Every store this record reads, taken ONCE and shared. -> dict

    Taken once so two hands on the same reel cannot disagree because they asked at different moments — the
    rule `end_routes.sources` and `printer._sources` both follow. `unreadable` names every store that exists
    and would not parse; `absent` names every store never written. The shelf listing is `shelf` (a set of
    reel directory names) or None when the hist directory could not be listed.
    """
    import end_routes as _er
    import read_pictures as _rp
    import river_stamp as _rs
    w = w or world(hist, stamp_path)
    # the four dict stores, with their absent/unreadable states, through their owner's loader. With an
    # explicit hist the owner is told so; with none it honours TV_HIST itself.
    src = _er.sources(hist)
    src["paths"] = dict(src.get("paths") or {}, **w)
    src["unreadable"] = list(src.get("unreadable") or [])
    src["absent"] = list(src.get("absent") or [])
    # the tombstone ledger as a mapping keyed by reel, so lookup_either_way can ask it like the others.
    # ⚠ the ledger is a LIST in the file (`{reels: [...]}`); a row with no reel name is counted, never keyed.
    tomb_rows = (src.get("ledger") or {}).get("reels") if isinstance(src.get("ledger"), dict) else None
    # ⚠ MEASURED 2026-09-29 on his ledger: 460 rows, 459 distinct reels — one reel is recorded as removed TWICE,
    # and that same reel is still on the shelf. The LAST row wins the lookup (it is the latest act), and the
    # count of rows per reel is kept beside it so a second removal is never folded into the first.
    src["tombByReel"], src["tombNameless"], src["tombRowsByReel"] = {}, 0, {}
    if isinstance(tomb_rows, list):
        for r in tomb_rows:
            if isinstance(r, dict) and str(r.get("reel") or "").strip():
                k = str(r["reel"]).strip()
                src["tombByReel"][k] = r
                src["tombRowsByReel"][k] = src["tombRowsByReel"].get(k, 0) + 1
            else:
                src["tombNameless"] += 1
    # the river's memory. rows() says ok=False only when the store exists and would not read.
    rep = _rs.rows(w["river_stamp"])
    src["stamps"] = rep.get("rows") if rep.get("ok") else None
    src["stampsState"] = "ok" if rep.get("ok") else "unreadable"
    src["stampsWhy"] = rep.get("why") or ""
    if not rep.get("ok"):
        src["unreadable"].append(os.path.basename(w["river_stamp"]))
    elif rep.get("everStamped") is False:
        src["absent"].append(os.path.basename(w["river_stamp"]))
    # the recorder's own records: [] for never written, None for exists-and-will-not-read (read_pictures' rule)
    src["reaps"] = _rp.load_jsonl(w["reel_reaps"])
    src["refusals"] = _rp.load_jsonl(w["read_pictures"])
    for key, nm in (("reaps", "reel_reaps"), ("refusals", "read_pictures")):
        if src[key] is None:
            src["unreadable"].append(os.path.basename(w[nm]))
        elif not os.path.exists(w[nm]):
            src["absent"].append(os.path.basename(w[nm]))
    # the shelf: which reel directories exist right now
    try:
        src["shelf"] = set(d for d in os.listdir(w["hist"])
                           if d.startswith("reel_") and os.path.isdir(os.path.join(w["hist"], d)))
        src["shelfWhy"] = ""
    except OSError as e:
        src["shelf"] = None
        src["shelfWhy"] = "the shelf at %s could not be listed (%s)" % (os.path.basename(w["hist"]),
                                                                        type(e).__name__)
    # the witness index: which sessions the durable stores cite. ok=False when ANY of them was unreadable.
    try:
        import frame_authority as _fa
        src["witness"] = _fa.witness_index(w["witness_root"])
    except Exception as e:
        src["witness"] = {"ok": False, "sessions": set(), "why": type(e).__name__}
    return src


# ══ ONE REEL ════════════════════════════════════════════════════════════════════════════════════════════════

def _names(reel):
    """-> (reel directory name, bare session id). A bare `s_<ms>_<n>` is accepted and prefixed; a prefixed
    name is never re-prefixed (REG-565)."""
    import reel_retention as _rr
    r = str(reel or "").strip()
    if not r:
        return "", ""
    b = _rr.bare_reel(r)
    return ("reel_" + b) if b else r, b


def _lookup(store, state, reel):
    """One reel's row in a store keyed either way. -> (row | None, held)

    held is None when the store is UNREADABLE (its state says so), False when it was read (or never written)
    and holds no row, True when a row is there. The lookup rule is the owner's, never a copy.
    """
    if state == "unreadable":
        return None, None
    if not isinstance(store, dict):
        return None, False
    import reel_retention as _rr
    row = _rr.lookup_either_way(store, reel)
    return row, (row is not None)


def _hand(name, held, at, why, **facts):
    """The one shape every hand answers in. `held` is the three-valued fact; `at` is that hand's OWN clock
    (None = it carries none), and `by` names the writer so a reader never has to guess who said it."""
    h = {"holder": name, "held": held, "at": at, "by": WRITER[name], "why": why}
    h.update(facts)
    return h


def _int(v):
    return v if (isinstance(v, int) and not isinstance(v, bool)) else None


def _recorder(reel, session, src, list_frames):
    """The recorder's hand: is the directory on the shelf, when was it filmed, and what do the recorder's own
    records say it took or refused. `list_frames` counts frames only when asked (the census never asks — a
    listing per reel over a growing folder is the scar a_watcher_over_a_growing_folder)."""
    shelf = src.get("shelf")
    hist = src["paths"]["hist"]
    on_disk = None if shelf is None else (reel in shelf)
    at, clock, frames = None, None, None
    if on_disk:
        try:
            import reel_router as _rr
            at, clock = _rr._captured_ms(reel, hist)
        except Exception:
            at, clock = None, None
        if list_frames:
            try:
                import frame_ref as _fr
                names = _fr.listing(os.path.join(hist, reel))
                frames = None if names is None else sum(1 for nm, _k, _s in names
                                                        if str(nm).lower().endswith(".jpg"))
            except Exception:
                frames = None
    # the recorder's reap record: rows naming this reel. None = the record could not be read.
    reaps = src.get("reaps")
    mine = None
    if reaps is not None:
        mine = [r for r in reaps if str(r.get("reel") or "") in (reel, session)]
    removed = None if mine is None else any(bool(r.get("removed")) for r in mine)
    last_reap = None if not mine else max((_int(r.get("ts")) or 0) for r in mine) or None
    # REG-1678 — a reap row says what the river had the reel at when it was taken. True only when a row that
    # REMOVED it carries readOwed true; a row from before the field (or one where the river could not be asked)
    # says nothing either way, and None is never read as "it was finished". [[unknown-stays-unknown]]
    owed_rows = [] if not mine else [r for r in mine if r.get("removed") and r.get("readOwed") is True]
    reaped_owed = None if mine is None else bool(owed_rows)
    reaped_at = (owed_rows[-1].get("riverStation") or "no stamp at all") if owed_rows else None
    # the recorder's refusal record: pictures it did NOT write for this session (disk floor / budget)
    refusals = src.get("refusals")
    refused = None
    if refusals is not None:
        refused = [r for r in refusals if str(r.get("session") or "") == session and r.get("why") != "saved-small"]
    if on_disk is None:
        why = src.get("shelfWhy") or "the shelf could not be listed, so whether this reel is on it is UNKNOWN"
    elif on_disk:
        why = "on the shelf%s" % ((", filmed %s (clock: %s)" % (_when(at), clock)) if at else "")
    elif removed:
        why = "not on the shelf — the recorder's own reap record says its reaper removed it on %s" % _when(last_reap)
    else:
        why = "not on the shelf, and the recorder's reap record does not name it"
    return _hand("recorder", on_disk, at, why, clock=clock, frames=frames,
                 reaps=(None if mine is None else len(mine)), removedByReaper=removed,
                 reapedReadOwed=reaped_owed, reapedAtStation=reaped_at,
                 refusals=(None if refused is None else len(refused)))


def _triage(reel, src):
    """The survey's hand: has retro_triage walked it, in full or in part, and what did it find."""
    row, held = _lookup(src.get("structural"), src.get("structuralState"), reel)
    if held is None:
        return _hand("triage", None, None, "retro_triage.json exists and will not parse — whether the survey "
                                            "ever walked this reel is UNKNOWN", full=None, panels=None)
    if not held:
        return _hand("triage", False, None, "no structural pass has ever recorded this reel", full=None,
                     panels=None)
    full = bool(row.get("full"))
    # `panels` is the key retro_triage.remember writes (its `hits` argument lands under that name)
    panels = _int(row.get("panels"))
    return _hand("triage", True, _int(row.get("ts")),
                 "surveyed %s on %s: %s panel frame(s)" % ("IN FULL" if full else "in part",
                                                          _when(row.get("ts")),
                                                          "?" if panels is None else panels),
                 full=full, panels=panels)


def _reads_for(rows, reel, session, src):
    """The journal's reads that named something IN THIS REEL, and whether their pictures are still there.
    -> dict | None (None = no journal was handed in: not asked, which is not 'no reads').

    ⚠ THE WHOLE JOURNAL, NOT THE DOCTOR'S 24 h WINDOW — custody is not a freshness question. The read rows are
    read_pictures.named_reads' (its rule for what counts as a read that named something), the picture answer
    is read_pictures.locator + who_took, bounded to the first 40 reads as /api/picture_status bounds itself."""
    if rows is None:
        return None
    import frame_ref as _fr
    import read_pictures as _rp
    named = _rp.named_reads(rows, int(time.time() * 1000), window_ms=float("inf"))
    mine = [r for r in named if r.get("sessionId") == session or _fr.reel_of(r.get("frameId")) == reel]
    out = {"n": len(mine), "firstTs": None, "lastTs": None, "names": [],
           "pictures": {"onDisk": None, "gone": None, "unknown": None, "goneWhy": []}}
    if not mine:
        return out
    ts = sorted(r["ts"] for r in mine if r.get("ts"))
    out["firstTs"], out["lastTs"] = (ts[0], ts[-1]) if ts else (None, None)
    seen = []
    for r in mine:
        for nm in r.get("names") or []:
            if nm not in seen:
                seen.append(nm)
    out["names"] = seen[:12]
    hist = src["paths"]["hist"]
    tombs = list((src.get("tombByReel") or {}).values())
    present = _rp.locator(hist) if hist and os.path.isdir(hist) else None
    if present is None:
        return out
    on, gone, unk = 0, 0, 0
    for r in mine[:40]:
        fid = r.get("frameId")
        p = present(fid) if fid else False
        if p is None:
            unk += 1
        elif p:
            on += 1
        else:
            gone += 1
            if len(out["pictures"]["goneWhy"]) < 3:
                code, words = _rp.who_took(fid or "", src.get("reaps"), tombs, src.get("refusals"),
                                           r.get("ts"), session)
                out["pictures"]["goneWhy"].append("%s — %s" % (fid or "?", words))
    out["pictures"].update({"onDisk": on, "gone": gone, "unknown": unk})
    return out


def _printer(reel, session, src, reads):
    """The printer's hand: the chronicle sweep's seal, and the reads the journal holds for this reel."""
    row, held = _lookup(src.get("chronicle"), src.get("chronicleState"), reel)
    rd = _reads_for(reads, reel, session, src)
    if held is None:
        return _hand("printer", None, None, "chronicle_swept.json exists and will not parse — whether the "
                                             "chronicle lane ever read this reel is UNKNOWN", pages=None,
                     promptVer=None, reads=rd)
    if not held:
        n = None if rd is None else rd.get("n")
        why = ("the chronicle lane has never recorded this reel"
               + ("" if not n else " — but the journal holds %d read(s) that named something in it" % n))
        # ⚠ a read in the journal IS the printer's hand on the reel, seal or no seal: PRINTER on the river
        # means exactly "names read and no seal yet". held stays False for the SEAL and the reads say so.
        return _hand("printer", False, None, why, pages=None, promptVer=None, reads=rd)
    pages = _int(row.get("pages"))
    return _hand("printer", True, _int(row.get("ts")),
                 "chronicle seal on %s: %s page(s) banked (reader %s)%s"
                 % (_when(row.get("ts")), "?" if pages is None else pages, row.get("promptVer") or "?",
                    (" — " + str(row.get("why"))[:120]) if row.get("why") else ""),
                 pages=pages, promptVer=row.get("promptVer"), reads=rd)


def _vault(reel, session, src):
    """The vault's hand: the vault sweep's seal, what that seal certifies, and whether the durable stores
    cite this session as a witness (a cited frame is never drained — his §26)."""
    import frame_authority as _fa
    row, held = _lookup(src.get("vault"), src.get("vaultState"), session)
    wi = src.get("witness") or {}
    cited = None if not wi.get("ok") else (session in (wi.get("sessions") or set()))
    if held is None:
        return _hand("vault", None, None, "vault_swept.json exists and will not parse — whether the vault "
                                           "lane ever sealed this reel is UNKNOWN", verdict=None, rows=None,
                     cited=cited)
    if not held:
        return _hand("vault", False, None, "the vault lane has never sealed this session"
                     + (" — but the durable stores CITE it as a witness" if cited else ""),
                     verdict=None, rows=None, cited=cited)
    verdict, vwhy = _fa.seal_verdict(row)
    return _hand("vault", True, _int(row.get("ts")),
                 "vault seal on %s: %s — %s" % (_when(row.get("ts")), verdict, vwhy[:160]),
                 verdict=verdict, rows=_int(row.get("rows")), promptVer=row.get("promptVer"), cited=cited)


def _tombstone(reel, src, plan):
    """The deleter's hand: the ledger row (an act, dated), the door end_routes says it left by, and — for a
    reel still on the shelf — the deleter's CURRENT intent from the plan, labelled as intent, never as an act."""
    state = src.get("ledgerState")
    row, held = _lookup(src.get("tombByReel"), state, reel)
    intent = _intent(reel, plan)
    if held is None:
        return _hand("tombstone", None, None, "reel_tombstones.json exists and will not parse — whether this "
                                               "reel was ever closed out is UNKNOWN", claimsBothSeals=None,
                     door=None, intent=intent)
    if not held:
        return _hand("tombstone", False, None, "no tombstone — the ledger does not record this reel as removed",
                     claimsBothSeals=None, door=None, intent=intent)
    why_txt = row.get("why")
    # REG-3293 - the deleter's sentence now names the seals it held; "seals held: chronicle and vault" is the both-seals
    # claim, and the old fixed sentence still counts as one (the history it wrote stays reported, never excused)
    import reel_retention as _rr_s           # one sentence, one owner: the deleter that writes it
    claims = None if why_txt is None else (BOTH_LANES in str(why_txt) or _rr_s.SEALS_BOTH in str(why_txt))
    door = None
    try:
        import end_routes as _er
        v = _er.verdict(reel, src=src)
        door = {"say": v.get("say"), "door": v.get("door"), "why": str(v.get("why") or "")[:200]}
    except Exception as e:
        door = {"say": "UNKNOWN", "door": None, "why": "end_routes would not answer (%s)" % type(e).__name__}
    n_rows = (src.get("tombRowsByReel") or {}).get(reel) or 1
    return _hand("tombstone", True, _int(row.get("deletedTs")),
                 "closed out on %s: %s MB, %s frame(s), its own sentence: %s%s"
                 % (_when(row.get("deletedTs")), row.get("mb"), row.get("frames"),
                    (str(why_txt)[:120] if why_txt else "(none)"),
                    (" ⚠ the ledger holds %d rows for this reel — recorded as removed %d times" % (n_rows, n_rows)
                     if n_rows > 1 else "")),
                 ledgerRows=n_rows,
                 claimsBothSeals=claims, mb=row.get("mb"), frames=_int(row.get("frames")),
                 pages=_int(row.get("pages")), startedTs=_int(row.get("startedTs")),
                 kept=(len(row["kept"]) if isinstance(row.get("kept"), list) else None),
                 door=door, intent=intent)


def _intent(reel, plan):
    """What the deleter would do NOW, from reel_retention.plan()'s own rows. -> dict | None (not asked)."""
    if not isinstance(plan, dict):
        return None
    if not plan.get("ok"):
        return {"say": "UNKNOWN", "why": str(plan.get("why") or "the plan would not answer")[:160]}
    import reel_retention as _rr
    for key, say in (("candidates", "candidate"), ("kept", "kept")):
        for r in plan.get(key) or []:
            if isinstance(r, dict) and _rr.bare_reel(str(r.get("reel") or "")) == _rr.bare_reel(reel):
                return {"say": say, "tag": r.get("tag"), "why": str(r.get("why") or "")[:160]}
    return {"say": "not-planned", "why": "the plan names neither a candidate nor a kept row for this reel"}


def _journey(reel, src):
    """The river's own memory of this reel, quoted: the stations it reached, and the lane at the last one."""
    import river_stamp as _rs
    import river_walk as _rw
    stamps = src.get("stamps")
    if stamps is None:
        return {"ok": False, "stations": [], "current": None, "lane": None,
                "why": "UNKNOWN, not an empty journey — %s" % (src.get("stampsWhy") or "the stamp store could not be read")}
    mine = [r for r in stamps if str(r.get("reel")) == reel]
    cur = mine[-1].get("station") if mine else None
    lane = (_rw.LANE_OF_STATION.get(cur) or {}).get("lane") if cur else None
    out = {"ok": True, "stations": [{"station": r.get("station"), "at": r.get("at"), "by": r.get("by"),
                                     "byKind": r.get("byKind"), "from": r.get("from")} for r in mine],
           "current": cur, "lane": lane, "n": len(mine),
           "why": ("" if mine else "this reel has no stamp at all — it has never been walked with a stamper "
                                  "attached. `current` is None because nobody looked, not because it is nowhere")}
    return out


def _contradictions(reel, hands, journey):
    """Two writers disagreeing about one reel. -> [rows], each with both sides named.

    ⚠ NEVER RAISED ON AN UNKNOWN SIDE. A store that could not be read has said nothing, and "the vault never
    sealed it" is not a thing an unreadable vault_swept.json can be quoted as saying.
    """
    h = {x["holder"]: x for x in hands}
    out = []
    t, v, p, r = h["tombstone"], h["vault"], h["printer"], h["recorder"]
    if t["held"] is True and t.get("claimsBothSeals") is True:
        missing = []
        if v["held"] is False:
            missing.append("vault_swept.json holds no seal for it")
        if p["held"] is False:
            missing.append("chronicle_swept.json holds no seal for it")
        if missing:
            out.append({"kind": "tombstone-claims-seals",
                        "left": {"who": WRITER["tombstone"], "says": "\"%s\"" % BOTH_LANES},
                        "right": {"who": "the seal stores", "says": " and ".join(missing)},
                        "why": "the permanent record of an irreversible delete names a hand whose own "
                               "record never touched the reel"})
    if t["held"] is True and r["held"] is True:
        out.append({"kind": "deleted-but-present",
                    "left": {"who": WRITER["tombstone"], "says": "closed out on %s" % _when(t.get("at"))},
                    "right": {"who": WRITER["recorder"], "says": "the directory is still on the shelf"},
                    "why": "the ledger records a removal the shelf does not show"})
    if r.get("reapedReadOwed") is True:
        out.append({"kind": "reaped-before-extracted",
                    "left": {"who": WRITER["recorder"], "says": "its disk floor removed the reel"},
                    "right": {"who": "river_stamp", "says": "it was at %s - a read was still owed"
                                                            % (r.get("reapedAtStation") or "?")},
                    "why": "his chain is extract, tombstone, then delete; this footage left before its "
                           "items were read, because the disk was full"})
    if journey.get("ok") and journey.get("current") == "TOMBSTONE" and t["held"] is False:
        out.append({"kind": "stamped-tombstone-no-ledger-row",
                    "left": {"who": "river_stamp (%s)" % ((journey["stations"][-1].get("by") or "?")
                                                          if journey.get("stations") else "?"),
                             "says": "reached TOMBSTONE"},
                    "right": {"who": WRITER["tombstone"], "says": "no tombstone row"},
                    "why": "only the deleter writes a tombstone row; a TOMBSTONE stamp without one was made by "
                           "a hand, not by a removal"})
    return out


def custody(reel, src=None, reads=None, plan=None, hist=None, stamp_path=None, list_frames=True):
    """One reel's chain of custody. -> dict

    hands       one row per HOLDER, in custody order, each `held: True|False|None` with that hand's own facts
    current     the LAST hand whose store records the reel (None when no store does)
    entered     hands that held it · never   hands measured NOT to have (rooms never entered) ·
    unknown     hands whose store could not be read
    journey     river_stamp's memory, quoted — beside the hands, never folded into them
    contradictions  two writers disagreeing, both sides named
    `reads` is the reader's journal (rows) when the caller has it; None = not asked, which is not 'no reads'.
    `plan` is reel_retention.plan()'s dict when the caller has it; None = the deleter's intent is not asked.
    """
    reel, session = _names(reel)
    out = {"ok": False, "reel": reel, "session": session, "hands": [], "current": None, "entered": [],
           "never": [], "unknown": [], "journey": None, "contradictions": [], "unreadable": [], "why": ""}
    if not reel:
        out["why"] = "no reel was named, so there is no custody to look up"
        return out
    src = src if src is not None else sources(hist, stamp_path)
    hands = [_recorder(reel, session, src, list_frames), _triage(reel, src),
             _printer(reel, session, src, reads), _vault(reel, session, src), _tombstone(reel, src, plan)]
    journey = _journey(reel, src)
    out.update({"ok": True, "hands": hands, "journey": journey,
                "entered": [h["holder"] for h in hands if h["held"] is True],
                "never": [h["holder"] for h in hands if h["held"] is False],
                "unknown": [h["holder"] for h in hands if h["held"] is None],
                "contradictions": _contradictions(reel, hands, journey),
                "unreadable": list(src.get("unreadable") or [])})
    out["current"] = out["entered"][-1] if out["entered"] else None
    if not out["entered"] and not out["unknown"]:
        out["why"] = "no store on this PC records this reel — none yet, not nowhere"
    elif out["unknown"]:
        out["why"] = ("%s could not be read, so %s hand(s) are UNKNOWN — the chain is partial, not clean"
                      % (", ".join(out["unreadable"]) or "a store", len(out["unknown"])))
    elif out["contradictions"]:
        out["why"] = "%d contradiction(s): %s" % (len(out["contradictions"]),
                                                 ", ".join(c["kind"] for c in out["contradictions"]))
    else:
        out["why"] = "held by %s; never entered %s" % (", ".join(out["entered"]),
                                                       ", ".join(out["never"]) or "nothing — every room")
    return out


# ══ THE CENSUS — which hand holds each reel ═══════════════════════════════════════════════════════════════

def census(src=None, plan=None, hist=None, stamp_path=None, limit=200):
    """Every reel this PC has a record of — on the shelf OR in the tombstone ledger — and which hand holds it.
    -> dict. `rows` is capped at `limit` DRAWN; `n` and every count are over all of them, never the cap.

    ⚠ NO PER-REEL FRAME LISTING HERE. The census asks dict stores only (a_watcher_over_a_growing_folder: a
    listing per reel on every doctor tick is how a gate hung with a clean diff). The per-reel record lists.
    """
    src = src if src is not None else sources(hist, stamp_path)
    out = {"ok": False, "n": 0, "shelf": None, "tombstoned": None, "rows": [], "truncated": False,
           "byCurrent": {}, "contradictions": 0, "contradicted": 0, "byKind": {}, "firstContradicted": None,
           "unreadable": list(src.get("unreadable") or []), "absent": list(src.get("absent") or []),
           "unknownHands": 0, "duplicateTombstones": None, "namelessTombstones": None, "why": ""}
    shelf = src.get("shelf")
    tombs = src.get("tombByReel") if src.get("ledgerState") != "unreadable" else None
    if shelf is None and tombs is None:
        out["why"] = "neither the shelf nor the tombstone ledger could be read — the census is UNKNOWN, not empty"
        return out
    # REG-1678 — and every reel the recorder's disk floor took while the river still owed it a read: it is on
    # neither the shelf nor the ledger, so without this the one contradiction it carries is never looked at
    reaped_owed = set(str(r.get("reel")) for r in (src.get("reaps") or ())
                      if r.get("removed") and r.get("readOwed") is True and str(r.get("reel") or "").startswith("reel_"))
    names = sorted(set(shelf or ()) | set((tombs or {}).keys()) | reaped_owed)
    out.update({"ok": True, "n": len(names), "shelf": (None if shelf is None else len(shelf)),
                "tombstoned": (None if tombs is None else len(tombs)),
                # reels the ledger records as removed MORE THAN ONCE, and rows that name no reel at all —
                # both measured (0 = counted and none), None only when the ledger itself was unreadable
                "duplicateTombstones": (None if tombs is None else
                                        sum(1 for v in (src.get("tombRowsByReel") or {}).values() if v > 1)),
                "namelessTombstones": (None if tombs is None else int(src.get("tombNameless") or 0))})
    try:
        limit = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        limit = 200
    for nm in names:
        c = custody(nm, src=src, reads=None, plan=plan, list_frames=False)
        cur = c["current"] or "none"
        out["byCurrent"][cur] = out["byCurrent"].get(cur, 0) + 1
        out["unknownHands"] += len(c["unknown"])
        if c["contradictions"]:
            out["contradicted"] += 1
            out["contradictions"] += len(c["contradictions"])
            # v3526 (#231 second eye on v3525) — the FIRST contradicted reel over ALL reels, not over the rows kept:
            # past the draw cap the doctor named "first: ?" while its own count said there were some
            if out["firstContradicted"] is None:
                out["firstContradicted"] = {"reel": nm, "contradictions": [k["kind"] for k in c["contradictions"]]}
            for k in c["contradictions"]:
                out["byKind"][k["kind"]] = out["byKind"].get(k["kind"], 0) + 1
        if len(out["rows"]) < limit:
            out["rows"].append({"reel": nm, "current": c["current"], "entered": c["entered"],
                                "never": c["never"], "unknown": c["unknown"],
                                "contradictions": [k["kind"] for k in c["contradictions"]],
                                "station": (c["journey"] or {}).get("current")})
        else:
            out["truncated"] = True
    out["why"] = ("%d reel(s): %s on the shelf, %s tombstoned · %d contradiction(s) on %d reel(s)%s%s%s"
                  % (out["n"], "?" if out["shelf"] is None else out["shelf"],
                     "?" if out["tombstoned"] is None else out["tombstoned"],
                     out["contradictions"], out["contradicted"],
                     (" · %d hand(s) UNKNOWN (%s unreadable)" % (out["unknownHands"], ", ".join(out["unreadable"]))
                      if out["unreadable"] else ""),
                     (" · %d reel(s) tombstoned more than once" % out["duplicateTombstones"]
                      if out["duplicateTombstones"] else ""),
                     (" · %d of %d rows drawn" % (len(out["rows"]), out["n"]) if out["truncated"] else "")))
    return out


def doctor(src=None, hist=None, stamp_path=None):
    """The heart row 'reel custody'. PURE over `src`. -> (state, why), the doctor's own three words.

    UNKNOWN when any store this record reads could not be read, or the shelf could not be listed — a chain
    with an unreadable link is partial, and partial is not clean. MISSING when two writers contradict each
    other about any reel, naming how many and the first. OK otherwise, with its denominators said, because a
    clean chain over 0 reels and one over 493 are different sentences. [[unknown-stays-unknown]]
    """
    src = src if src is not None else sources(hist, stamp_path)
    if src.get("unreadable") or src.get("shelf") is None:
        return UNKNOWN, ("%s could not be read, so whether every reel's custody chain holds is UNKNOWN — not clean"
                         % (", ".join(src.get("unreadable") or []) or src.get("shelfWhy") or "the shelf"))
    c = census(src=src, limit=1000)
    if not c.get("ok"):
        return UNKNOWN, c.get("why") or "the census could not be taken"
    if c["contradicted"]:
        first = c.get("firstContradicted") or next((r for r in c["rows"] if r["contradictions"]), None)
        return MISSING, ("%d of %d reel(s) carry a custody contradiction (%s) — first: %s (%s). Two writers "
                         "disagree about the same reel; the record shows both"
                         % (c["contradicted"], c["n"],
                            ", ".join("%s ×%d" % (k, v) for k, v in sorted(c["byKind"].items())),
                            first["reel"] if first else "?", ", ".join(first["contradictions"]) if first else "?"))
    if c["n"] == 0:
        return OK, "no reel on the shelf and none in the tombstone ledger — nothing to hold custody of (measured, 0 of 0)"
    return OK, ("%d reel(s) (%d on the shelf, %d tombstoned) and every one's stores agree about who held it"
                % (c["n"], c["shelf"] or 0, c["tombstoned"] or 0))


def _when(ms):
    try:
        return time.strftime("%d %b %Y %H:%M", time.localtime(int(ms) / 1000.0))
    except Exception:
        return "an unknown date"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        from console_safe import enable as _enable
        _enable()
    except Exception:
        pass
    if argv:
        rec = custody(argv[0])
        print(json.dumps(rec, indent=1, ensure_ascii=False, default=str))
        return 0
    c = census()
    print(c["why"])
    for r in c["rows"]:
        print("  %-34s %-9s station %-9s entered %-40s never %s%s"
              % (r["reel"], r["current"] or "-", r["station"] or "-", ",".join(r["entered"]) or "-",
                 ",".join(r["never"]) or "-",
                 ("  ⚠ " + ",".join(r["contradictions"])) if r["contradictions"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
