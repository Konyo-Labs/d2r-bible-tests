#!/usr/bin/env python3
"""ONE HEALTH ENGINE — red/green flags for the console. IT REPORTS. IT NEVER REPAIRS.

Konyo, 2026-08-29: "not sure we need a live watchdog that FIXES things — might be wrong for the
console and make a bug worse.. but maybe a system that does red/green flag us.. so same here should
be a system working one unit system engine locked in... especially with all the fixes and versions
we shipped it makes things less messy going forward and keeps control"

⚠ REPORT, NEVER REPAIR — and he is right about why. An auto-healer can turn one fault into two and
do it unattended; a flag can only ever be wrong about a colour. Nothing in this module writes,
deletes, restarts or repairs anything, and a test pins that.

⚠ IT IS NOT AN AUTHORITY EITHER. frame_authority owns deletion. chronicle_retro owns grounding.
This engine reports ON them and decides nothing — otherwise two gates drift apart, which is the
exact defect class it exists to surface.

WHY IT EXISTS, in two measurements from the day it was written:

  · THE v2205 VAULT UNDO WAS ARMED ON EVERY BOARD since v2203, and would have dropped 273 of his
    280 owned names. Nothing on his console said so. It was found by reading code, not by any
    watching thing. That is check `armed_migration`, and it is the highest-value check here.

  · REGISTER FAILED FOR DAYS saying "this board build has no chronicleApply". The console's doctor
    rail had ALREADY diagnosed it — "the board is not open in the window" — in a paragraph of prose
    nobody reads. The information existed; the SURFACE did not. That is check `board_join`.

A check returns one of four states and UNKNOWN IS FIRST-CLASS:
    ok       measured, and fine
    warn     measured, and worth his attention
    blocked  measured, and something downstream cannot proceed
    unknown  COULD NOT BE MEASURED — never renders as ok. "The board is not open so its store
             cannot be asked" is not "the store is fine". [[unknown-stays-unknown]]
"""
import hashlib as _hashlib
import io
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OK, WARN, BLOCKED, UNKNOWN = "ok", "warn", "blocked", "unknown"


#: ══ WHAT EACH WATCHDOG FLAG WATCHES, IN THE REGISTRY'S OWN WORDS ═════════════════════════════
#: Same gap organ_matrix measured for the doctor, and the same fix: "watchdog names 7 thing(s),
#: and NONE of them resolves to any of the 58 surfaces — it is naming a different KIND of thing".
#: A flag is called `shadowWatch`; a surface is called `advanced-shadow`.
#:
#: ⚠ ONE ROW DOES NOT APPEAR HERE ON PURPOSE. `selfArming` DERIVES its surfaces from the lock list
#: it actually read, not from this map — `[l["lock"] for l in locks]` — so its coverage is
#: demonstrated by the row's own output rather than asserted beside it. That is strictly better
#: evidence, and where a row can produce it, it should. This map is for the rows that cannot.
#:
#: ⚠ AN EMPTY TUPLE IS A DECLARATION, NOT AN OMISSION, and a MISSING id fails the gate. Under-
#: claiming is the intended bias: a table reporting coverage it cannot demonstrate is worse than
#: an empty one. [[unknown-stays-unknown]] [[the-unjoined-end]]
WATCHES = {
    "lanes":           (),                     # store agreement, not a rendered surface
    # v3171 — the stash bank has no rendered surface yet; an empty tuple is a DECLARATION
    # that it is watched without a screen, never an omission. Under-claiming is the bias.
    "stashBank":       (),
    # ⚠ v3190 — FOUR FLAGS SHIPPED WITHOUT A DECLARATION AND THE LAW WAS RED ON CI THE WHOLE
    # TIME. A flag with no entry reads ABSENT in the organ table — a claim nobody made — which is
    # indistinguishable from a check nobody wrote. Each of these is declared with what it ACTUALLY
    # renders on, and an empty tuple where the honest answer is "watched, but not on a screen".
    "sweepMeter":      ("vault.sweep_start",),   # the rail meter reads the vault sweep's own state
    "vaultReceipts":   ("vault", "vault-full"),  # the receipt eye lives on the vault rows
    "vaultRemovals":   ("vault", "vault.forget"),
    # the attack tally is evidence ABOUT the lanes, not a rendered thing of its own
    "laneAttacks":     (),
    "armed_migration": (),
    "board_join":      (),
    "orphans":         ("_orphan_watch", "_orphan_exit_loop"),
    "shadowWatch":     ("advanced-shadow", "_shadow_watch_loop"),
    "readers":         (),
    # v3059 — the shelf's two rendered surfaces, declared because this row cannot derive them
    "shelfWitness":    ("shelf-cards", "river-strip"),
    # ⚠ v3098 — AN EMPTY TUPLE HERE IS A MEASUREMENT, NOT A SHRUG. This flag watches the read
    # METER, and the meter's panel (bible.html Tools -> Subscription) has NO render target in
    # organ_matrix — checked: 58 surfaces, none of them the meter. So it genuinely covers no
    # REGISTRY surface today, which is what the law asks an empty tuple to say. The gap is the
    # missing render target, and leaving the key out instead would have hidden it behind an
    # ABSENT row nobody could act on. This entry was missing entirely in v3092 and
    # `test_the_doctor_says_what_it_watches` was RED on the tree for six versions.
    "read_lanes_at_cap": (),
    # v3773 — click-to-paint on the board. The number is the page's own sample,
    # read from the ui beat. It renders on the vault because that is the room
    # whose paint froze the console. A beat that has not arrived is UNKNOWN.
    "inputLatency":    ("vault",),
    # selfArming is DERIVED — see the note above. It must not be listed here.
}


def _row(cid, state, line, evidence=None, measured_at=None, k=None, n=None, surfaces=None,
         surface_scores=None):
    """One flag. `line` is what he reads; `evidence` is what earned it.

    ★ v2438 — WILSON IS THE FIFTH ORGAN OF THE HEART, NOT A SIDE MODULE.
    Konyo, 2026-09-02: *"the heart should be wilson score too, not just doctor / eagle eye /
    watchdog / corroborator — wilson score embedded in it too."*

    So a row may carry `k` and `n` and the heart scores it here, in ONE place, for every check
    that has a proof history. A check with no history passes nothing and the field is absent —
    which is the point:

        `score: None`  nobody has tested this check      (UNPROVEN — work owed, not a fault)
        `score: 0.0`   it WAS tested and never refused   (INERT — the dangerous one)

    Collapsing those two is the exact failure a self-proving system cannot survive, because an
    invariant that always agrees may be perfect or inert and no amount of agreement separates
    them. [[heart-first]] §5 · [[unknown-stays-unknown]]

    ⚠ k and n count SABOTAGES ATTEMPTED and REFUSALS EARNED — never runs and passes. A score
    fed by pass-rate rises fastest for the check that is never exercised.
    """
    # ⚠ THE ORGAN'S OWN ANSWER TO "WHAT DO YOU WATCH", in the registry's vocabulary. Passed in
    # when the row can DERIVE it (selfArming reads the locks it judged); otherwise taken from
    # WATCHES, where a missing id fails the gate rather than defaulting to empty.
    _sf = list(surfaces) if surfaces is not None else list(WATCHES.get(cid, ()))
    row = {"id": cid, "state": state, "line": line, "surfaces": _sf,
           "evidence": list(evidence or []), "measuredAt": measured_at or int(time.time() * 1000)}
    if n is not None:
        try:
            n_i, k_i = int(n), int(k or 0)
        except (TypeError, ValueError):
            n_i, k_i = 0, 0
        row["proofK"] = k_i
        row["proofN"] = n_i
        # ⚠ PER-SURFACE SCORES, when the organ can tell them apart. One row carries ONE score, and
        # heart hands it to EVERY surface the row names — so a row naming twelve lanes must either
        # publish the weakest (understating the strong ones) or the strongest (crediting the weak
        # ones with evidence they never earned). Neither is true when the per-lane numbers are
        # known. A lane is as proven as ITS OWN sabotages, so the row may say so lane by lane.
        if isinstance(surface_scores, dict) and surface_scores:
            row["surfaceScores"] = dict(
                (str(_s), (round(float(_v), 4) if isinstance(_v, (int, float)) else None))
                for _s, _v in surface_scores.items())
        if n_i > 0:
            try:
                from confidence import wilson_lower     # one home for the maths — never a copy
                row["score"] = round(wilson_lower(k_i, n_i), 4)
            except Exception:
                row["score"] = None
        else:
            row["score"] = None          # untested is not zero
    return row


def _read_json(path):
    """-> (obj|None, why). None is UNREADABLE, which is never ok."""
    p = path if os.path.isabs(path) else os.path.join(HERE, path)
    if not os.path.exists(p):
        return None, "%s does not exist" % os.path.basename(p)
    try:
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh), ""
    except Exception as e:
        return None, "%s could not be read: %s" % (os.path.basename(p), e)


# ── CHECK 1 ─────────────────────────────────────────────────────────────────────────────────────
def check_lanes():
    """Are the extraction lanes doing work, and do they agree? Delegates to lane_health (v2272)."""
    try:
        import lane_health as LH
    except Exception as e:
        return _row("lanes", UNKNOWN, "lane health could not be loaded — %s" % e)
    rep = LH.report()
    bad = [l for l in rep["lanes"].values() if l["state"] == "stalled"]
    # ⚠⚠ v3265 — BLOCKED MUST STILL REACH HIM, OR THE THIRD STATE IS AN OFF SWITCH.
    # `lane_health` learned to say BLOCKED (owes work, can act on none of it) this same version.
    # This line existed before that word did, so the moment the new state shipped, a lane owing 4
    # reads would have fallen out of `bad`, matched nothing else, and landed on
    # "every extraction lane is fresh and aligned" — a GREEN HEART over the exact fault I was
    # fixing. A new verdict word is a JOIN, not a rename. [[the-unjoined-end]] [[regression-guard]]
    blk = [l for l in rep["lanes"].values() if l["state"] == "blocked"]
    unk = [l for l in rep["lanes"].values() if l["state"] == "unknown"]
    div = [d for d in rep["divergences"] if d["state"] == "diverged"]
    ev = [l["why"] for l in rep["lanes"].values()] + [d["why"] for d in rep["divergences"]]
    if unk:
        return _row("lanes", UNKNOWN, "a lane's store could not be read", ev)
    if bad or div or blk:
        # ⚠ a genuinely stopped lane and a disagreement both outrank BLOCKED, which is waiting on
        # a declaration rather than failing — so blocked leads only when it is the ONLY fault.
        worst = (bad + div + blk)[0]
        n = len(bad) + len(div) + len(blk)
        # ★ v2437 — THE DECIDING SENTENCE LEADS, BECAUSE THE CONSOLE ONLY PRINTS TWO.
        # console_doctor renders `"; ".join(_clip(x, 110) for x in evidence[:2])`, and `ev` was
        # built lanes-first, divergences-last. With two lanes and one divergence the [:2] kept
        # both "last did work N h ago" freshness lines and DROPPED the divergence — the only
        # sentence that says what is actually wrong. That is why CF-1 was filed as "chronicle
        # and vault both stopped doing work hours ago" when neither lane had stopped: both were
        # under their 48h threshold and owed 0, measured. The panel printed the word `missing`
        # over two sentences that describe a healthy lane.
        #
        # Fixed HERE rather than in the renderer: the consumer cannot know which of three
        # sentences is the deciding one, and this producer already computed `worst`. Every other
        # consumer of `evidence` gets the same ordering for free. [[the-unjoined-end]]
        ev = [worst["why"]] + [e for e in ev if e != worst["why"]]
        # ★ v2439 — "1 lane issue — chronicle+vault" DESCRIBED THE WRONG SHAPE. A cross-family
        # read of v2437's panel: "one issue, two lane names", and "it is a GAP BETWEEN TWO LANES,
        # not one lane failing". A stalled lane and a divergence are different faults with
        # different remedies, and the heading called them the same thing.
        if worst.get("pair"):
            head = "%s and %s disagree" % tuple(worst["pair"][:2])
        elif worst.get("state") == "blocked":
            # ⚠ NOT "has stopped". The remedy is different: a stopped lane needs its thread
            # looked at, a blocked lane needs the thing it is waiting for. Measured 2026-09-17:
            # the chronicle thread was alive, switched on and correct the whole time the panel
            # said STOPPED, and the word sent me hunting a fault that did not exist.
            head = "%s is blocked on %s owed read(s) it cannot act on" % (
                worst.get("lane"), worst.get("owed"))
        else:
            head = "%s has stopped" % worst.get("lane")
        return _row("lanes", WARN,
                    "%s%s" % (head, ("" if n == 1 else " (+%d more)" % (n - 1))),
                    ev)
    return _row("lanes", OK, "every extraction lane is fresh, unblocked and aligned", ev)



def check_shadow_watch():
    """Is the thing that is supposed to notice him playing actually looking?

    ★ THE FAILURE THIS EXISTS FOR: he played a whole evening with the shadow switch ON and got ZERO
    reels, because shadow only READ frames another mode had rolled. Nothing said so — the panel
    reported "armed", which is true and implies something false. A watcher that has never looked is
    the same defect wearing a different word. [[label-outlived-referent]]
    """
    try:
        import control_app as _ca
    except Exception as e:
        return _row("shadowWatch", UNKNOWN, "control_app will not import — %s" % str(e)[:70])
    try:
        st = _ca._shadow_state()
        w = _ca.shadow_watch_state()
    except Exception as e:
        return _row("shadowWatch", UNKNOWN, "could not read the watcher: %s" % str(e)[:70])
    if not isinstance(w, dict) or w.get("ok") is False:
        return _row("shadowWatch", UNKNOWN,
                    str((w or {}).get("why") or "the watcher's record is unreadable"))
    if not st.get("on"):
        # OFF means do not start another reel. A shadow reel already rolling is still judged:
        # saying "nothing is watching" while a 90-minute reel stacks up is the row going blind.
        try:
            _off = _ca._shadow_rollover_reading(w)
        except Exception as e:
            return _row("shadowWatch", UNKNOWN,
                        "the switch is off and the rolling reel could not be judged: %s" % str(e)[:60])
        if _off.get("state") in (WARN, UNKNOWN):
            return _row("shadowWatch", _off["state"],
                        "the shadow reader is switched OFF, and %s" % _off["line"])
        return _row("shadowWatch", OK, "the shadow reader is switched OFF, so nothing is watching "
                                       "for the game — by his choice")
    looked = w.get("lookedAt")
    if looked is None:
        return _row("shadowWatch", WARN,
                    "the shadow switch is ON and the watcher has NEVER looked for the game — "
                    "playing would produce nothing, which is exactly the evening that was lost")
    import time as _t
    age = (_t.time() * 1000.0 - float(looked)) / 60000.0
    if age > 10:
        return _row("shadowWatch", WARN,
                    "the shadow switch is ON but the watcher last looked %.0f minutes ago — it "
                    "should look every 20 s, so it is not running" % age)
    # ⏱ 2026-09-27 — THE HOURLY ROLLOVER, read from the SAME record. His order: a shadow session
    # closes every hour so it can be processed and nothing stacks up. A shadow reel older than the
    # limit plus a margin means the rollover STOPPED WORKING; a shadow reel whose start cannot be
    # read is UNKNOWN, never a clean row. The reading lives beside the rule in control_app, so the
    # limit, the margin and "current at the last look" have one owner. [[heart-first]]
    try:
        _rv = _ca._shadow_rollover_reading(w)
        _lane = _ca.shadow_watch_contract(st=st, w=w)
    except Exception as e:
        return _row("shadowWatch", UNKNOWN,
                    "could not judge the hourly rollover: %s" % str(e)[:70])
    _ev = ["lane: on=%s worked=%s lastTs=%s owed=%s" % (_lane.get("on"), _lane.get("worked"),
                                                        _lane.get("lastTs"), _lane.get("owed"))]
    if _rv.get("state") in (WARN, UNKNOWN):
        return _row("shadowWatch", _rv["state"], _rv["line"], _ev)
    # REG-1675 — the session that comes in parts: a clock hour that opened too many shadow reels
    try:
        _fr = _ca._shadow_fragment_reading(w)
    except Exception as e:
        return _row("shadowWatch", UNKNOWN, "could not judge whether this hour's sessions fragmented: %s" % str(e)[:60])
    # REG-1682 (the v3544 eye) — every state but the quiet one is said: an UNKNOWN reading fell through to the OK row
    if not isinstance(_fr, dict) or _fr.get("state") is not None:
        _fs = _fr.get("state") if isinstance(_fr, dict) else None
        return _row("shadowWatch", WARN if _fs == WARN else UNKNOWN,
                    (_fr.get("line") if isinstance(_fr, dict) else "") or
                    "whether this hour's shadow sessions fragmented could not be judged", _ev)
    return _row("shadowWatch", OK,
                "watching for the game every 20 s (last look %.0f s ago) · %s reel(s) started · "
                "%s rolled over on the hour · %s"
                % (age * 60, w.get("starts") or 0, w.get("rotations") or 0,
                   str(w.get("why") or "")[:80]), _ev)



def check_readers_agree():
    """Are the two game readers still calibrated to the same screen?

    stash_eye (left-anchored panel) and chronicle_template (centered modal) each carry their own
    calibration film of HIS monitor. The geometry differs for a real reason; the SCREEN does not.
    A recalibration of one is silent in the other, and the symptom is a reader that quietly stops
    finding panels rather than an error anyone sees. [[copy-drift]]
    """
    try:
        import stash_eye as _se
        import chronicle_template as _ct
    except Exception as e:
        return _row("readers", UNKNOWN, "a reader will not import — %s" % str(e)[:70])
    a = getattr(_se, "_CROP_CAL_FILM", None)
    b = getattr(_ct, "_CAL_FILM", None)
    if not a or not b:
        return _row("readers", UNKNOWN,
                    "one reader does not publish its calibration film, so they cannot be compared")
    if tuple(a) != tuple(b):
        return _row("readers", WARN,
                    "the two readers are calibrated to DIFFERENT screens — stash_eye %s vs "
                    "chronicle_template %s. One was re-measured and the other was not; the stale "
                    "one will quietly stop finding its panel." % (tuple(a), tuple(b)))
    return _row("readers", OK,
                "both readers calibrated to the same screen %s (aspect %.4f)"
                % (tuple(a), a[0] / float(a[1])))


# ── CHECK 2 — the one that would have caught the loaded gun ─────────────────────────────────────
#: destructive one-shot blocks, and the SHAPE of a record that proves they may fire.
#: Each entry: (id, human name, the flag whose PRESENCE used to be trusted, the file it lives in)
#: ⚠ v2281 — NO HARDCODED NAMES. The first cut carried ONE tuple naming d2r_vaultBackfill_v2200 by
#: hand, so it caught the v2205 loaded gun only because I already knew the answer — and it would not
#: have caught the next one, which is the only thing a watching check is for.
#:
#: The class IS mechanically findable, and the two polarities are opposites:
#:   `if (LSR.getItem(F)) return;`   — "already done, skip".  SAFE. A stray stamp DISABLES the block.
#:   `if (!LSR.getItem(F)) return;`  — "run ONLY when F is set". ARMED the moment anything else
#:                                     stamps F unconditionally, which is exactly what a RETIREMENT
#:                                     does. That was v2205: a retired migration stamped the flag on
#:                                     every load and a destructive undo trusted its presence.
#: Measured on bible.html 2026-08-30: 4 sites of the safe shape, 0 of the dangerous one. The 4/0
#: split is what makes the zero a measurement rather than a vacuous pass. [[regression-guard]]
#: ⚠ THE GATES USE CONSTANTS, NOT LITERALS. My first reader matched `LSR.getItem('flag')` and found
#: NOTHING, because every real site reads `if (window.LSR.getItem(DONE)) return;` with the flag name
#: bound above as `var DONE = 'd2r_...'`. The check said so out loud — UNKNOWN, "a broken reader,
#: not a clean tree" — instead of reporting a green sweep over zero sites, which is the whole reason
#: that branch exists. [[source-reading-guard]] [[feedback-suspect-the-instrument]]
_GATE_RE = re.compile(
    r"if\s*\(\s*!\s*(?:window\.)?LSR\.getItem\(\s*([A-Za-z0-9_']+)\s*\)\s*\)\s*return")
_SAFE_RE = re.compile(
    r"if\s*\(\s*(?:window\.)?LSR\.getItem\(\s*([A-Za-z0-9_']+)\s*\)\s*\)\s*return")
_CONST_RE = re.compile(r"(?:var|let|const)\s+([A-Za-z0-9_]+)\s*=\s*'([A-Za-z0-9_]+)'\s*;")


def _flag_of(token, src):
    """A gate names either the flag itself or a const bound to it. -> (flag, how) or (None, why)."""
    t = token.strip()
    if t.startswith("'"):
        return t.strip("'"), "literal"
    for name, val in _CONST_RE.findall(src):
        if name == t:
            return val, "const %s" % t
    return None, "the gate reads %s and nothing binds it — UNRESOLVED" % t


def armed_flags(src):
    """Every flag gated in the DANGEROUS polarity that something else also stamps. -> list of dicts.

    Pure, so it can be tested against a reconstruction of the pre-v2275 bytes without a browser.
    """
    out = []
    for m in _GATE_RE.finditer(src):
        flag, how = _flag_of(m.group(1), src)
        if not flag:
            # ⚠ an unresolvable gate is NOT a safe gate. Report it so it cannot pass silently.
            out.append({"flag": m.group(1), "stamps": -1, "retiredStamp": 0, "how": how,
                        "unresolved": True, "at": m.start()})
            continue
        stamped = len(re.findall(r"setItem\(\s*'%s'" % re.escape(flag), src))
        # the DONE-const form: `setItem(DONE, ...)` where DONE binds this flag
        for name, val in _CONST_RE.findall(src):
            if val == flag:
                stamped += len(re.findall(r"setItem\(\s*%s\s*," % re.escape(name), src))
        retired = len(re.findall(
            r"setItem\([^)]{0,40}?JSON\.stringify\(\s*\{\s*retired", src))
        if stamped:
            out.append({"flag": flag, "stamps": stamped, "retiredStamp": retired, "how": how,
                        "unresolved": False, "at": m.start()})
    return out


def check_armed_migrations():
    """Is a destructive one-shot able to fire on a board right now?

    ⚠ SOURCE-LEVEL ON PURPOSE. It cannot read his board's localStorage from here — that store is
    pywebview/WebKit and this process does not own it — so it asks the only question it can answer
    honestly: does the SHIPPED CODE still gate a destructive block on a flag that something else
    stamps unconditionally? That is exactly the v2205 defect and it is checkable without touching
    his data.
    """
    try:
        with io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
    except Exception as e:
        return _row("armed_migration", UNKNOWN, "bible.html could not be read — %s" % e)
    armed = armed_flags(src)
    safe = len(_SAFE_RE.findall(src))
    ev = ["%d gate(s) in the safe polarity (already-done, skip)" % safe,
          "%d gate(s) in the v2205 polarity (runs ONLY when the flag is set)"
          % len(_GATE_RE.findall(src))]
    if armed:
        a = armed[0]
        ev = [("%s: UNRESOLVED — %s" % (x["flag"], x["how"])) if x.get("unresolved")
              else ("%s (%s): stamped %d×%s" % (x["flag"], x["how"], x["stamps"],
                    ", RETIREMENT stamp present" if x["retiredStamp"] else ""))
              for x in armed] + ev
        return _row("armed_migration", BLOCKED,
                    "%d destructive one-shot(s) ARMED — %s gates on a flag that is stamped "
                    "elsewhere" % (len(armed), a["flag"]), ev)
    # ⚠ a zero here is only a measurement because the SAFE polarity is found too. If neither shape
    # is found the reader is broken, not the code, and that must not read as clean.
    if not safe and not _GATE_RE.findall(src):
        return _row("armed_migration", UNKNOWN,
                    "no one-shot gate of EITHER polarity was found, so this check matched nothing "
                    "at all — that is a broken reader, not a clean tree", ev)
    return _row("armed_migration", OK,
                "no destructive one-shot gates on a flag that is stamped unconditionally", ev)


# ── CHECK 3 — the one the doctor rail already knew and could not say ────────────────────────────
def check_board_join(evaluate=None, payload=None):
    """Is the console able to reach the BOARD, or is it about to ask itself?

    `evaluate` is an injected callable (page_js) -> value, so this stays testable and so this module
    never reaches for a window itself. Absent, the answer is UNKNOWN — not ok.
    """
    # v2277 — THE PAYLOAD PATH IS THE ONE THAT ACTUALLY RUNS. Nothing on the console holds a
    # window handle it can hand this module, so the `evaluate` door was a tap nobody could open and
    # the flag sat UNKNOWN forever. board_ownership already reaches into the board and now reports
    # `hasChronicleApply`, so the console rail answers from a real read of the real window.
    # [[plumbing-with-no-tap]]
    if payload is not None:
        if not isinstance(payload, dict) or not payload.get("ok"):
            why = (payload or {}).get("why") if isinstance(payload, dict) else None
            return _row("board_join", UNKNOWN,
                        "the board did not answer, so whether registering can work is unmeasured"
                        "%s" % ((" — %s" % str(why)[:80]) if why else ""))
        if "hasChronicleApply" not in payload:
            return _row("board_join", UNKNOWN,
                        "this console build does not report hasChronicleApply — nobody asked, "
                        "which is not the same as 'it is fine'")
        path = str(payload.get("path") or "?")
        if payload.get("hasChronicleApply"):
            return _row("board_join", OK, "the board is reachable at %s" % path,
                        ["chronicleApply present"])
        # CF-2 — path=/ without chronicleApply is the CONSOLE. Register already leaves a
        # localStorage note the board drains (v2289). Calling that a BLOCKED fault is the
        # tautology that taught him to skip the row. The note door is the join.
        if payload.get("canHandoff"):
            # ⚠⚠ v2454 — THE REFRAME ABOVE IS RIGHT AND THE STATE WAS NOT. Calling a designed
            # handoff path BLOCKED is the tautology that taught him to skip the row — that part
            # stands. But this shipped as OK, and OK is a claim larger than its evidence.
            #
            # MEASURED, control_app.py:11406 — the flag it rests on is:
            #     var canHandoff = !!(window.LSR && window.LSR.setItem);
            # That proves A LOCALSTORAGE WRITER OBJECT EXISTS. It does not prove a note was
            # written, that the board drained it, or that any handoff ever completed. An OK built
            # on "the capability is present" is exactly how an unjoined end hides, and this repo
            # treats a claim larger than its evidence as the one unforgivable direction.
            #
            # UNKNOWN is both honest and useful, and it composes with CF-8: the row now carries
            # its own age, so "unaskable for 5 minutes" and "for 45 hours" stop looking identical.
            # OK becomes correct the moment there is a drained marker or an acknowledgement from
            # the board side — a signal that a handoff COMPLETED, not that it could be attempted.
            # [[unknown-stays-unknown]] [[the-unjoined-end]]
            return _row("board_join", UNKNOWN,
                        "this window is %s and has no chronicleApply; registering leaves a note "
                        "the board drains, and no handoff has been confirmed from here. That is "
                        "the designed door, not a broken one — but nobody has seen it complete."
                        % path,
                        ["path=%s" % path, "handoff note available",
                         "no drained-note confirmation"])
        return _row("board_join", BLOCKED,
                    "the window that answered is %s and has no chronicleApply — registering "
                    "cannot work from here%s" % (path,
                    " (that path is the CONSOLE, not the board)" if path in ("/", "") else ""),
                    ["path=%s" % path, "chronicleApply absent"])
    if evaluate is None:
        return _row("board_join", UNKNOWN,
                    "the board window was not offered to this check, so whether the console can "
                    "reach it is unmeasured — that is not the same as 'it is fine'")
    try:
        raw = evaluate("(function(){return JSON.stringify({p:location.pathname,"
                       "has:typeof window.chronicleApply==='function'})})()")
        got = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception as e:
        return _row("board_join", UNKNOWN, "the board window did not answer — %s" % e)
    if not isinstance(got, dict) or "has" not in got:
        return _row("board_join", UNKNOWN, "the board window answered something unreadable")
    path = str(got.get("p") or "?")
    if got.get("has"):
        return _row("board_join", OK, "the board is reachable at %s" % path, ["chronicleApply present"])
    return _row("board_join", BLOCKED,
                "the window answered from %s and has no chronicleApply — registering cannot work "
                "from here%s" % (path, " (that path is the CONSOLE, not the board)" if path in ("/", "") else ""),
                ["location.pathname=%s" % path, "chronicleApply absent"])


# ── CHECK 4 ─────────────────────────────────────────────────────────────────────────────────────
def check_orphans():
    # ⚠ v3135 (#80) — the same join as laneLiveness: attacks that ACTUALLY RAN against
    # this organ's own module, read from heart2's record. Computed BEFORE the branches so
    # a bad verdict cannot cost the row its proof history. [[the-unjoined-end]]
    # ⚠⚠⚠ v3136 — NAMED _atkK/_atkN BECAUSE `_n` ALREADY MEANT SOMETHING HERE, AND I CLOBBERED IT.
    # This function's OK path sets `_n = len(_cpu_sample())` — the number of PROCESSES SCANNED,
    # hundreds on a Mac — and then returns. v3135 passed `n=_n` on that return, so `proofN` became
    # the process count and `wilson_lower(6, 250)` published ~0.008 as this organ's score.
    # WORSE: with the tally unknown, `k=None` becomes `int(None or 0) == 0` against n=250, so the
    # row published `score: 0.0` — INERT, "it WAS tested and never refused" — which is exactly the
    # UNKNOWN that `_attack_tally` returns (None, None) to protect. A name collision turned the
    # safest answer into the most dangerous one. Caught by the second eye; I had edited a function
    # without reading its whole body. [[source-window-shortcut]]
    _atkK, _atkN = _attack_tally("my_orphans")
    """Anything of ours busy AND old — the 28-hour core-burner class."""
    try:
        import my_orphans as MO
    except Exception as e:
        return _row("orphans", UNKNOWN, "the orphan sweep could not be loaded — %s" % e, k=_atkK, n=_atkN)
    rows = MO.suspects()
    # ⚠⚠ A ROW WITH NO PID IS NOT A PROCESS — IT IS THE SWEEP SAYING IT COULD NOT JUDGE.
    # `suspects()` uses that shape for "ps could not be asked" and, since v2848, for "only one CPU
    # sample exists so far" (the second now comes from the PREVIOUS call instead of a 4-second
    # sleep, because this runs on the watchdog's ten-minute timer). Counting those as suspects
    # produced `1 process(es) busy and old, and nothing can say whose they are` on a machine where
    # the sweep had simply not measured twice yet — a confident sentence about a process that does
    # not exist. UNMEASURED and UNATTRIBUTED are different answers.
    # [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    _unmeasured = [r for r in rows if not r.get("pid")]
    rows = [r for r in rows if r.get("pid")]
    if _unmeasured and not rows:
        return _row("orphans", UNKNOWN,
                    "the sweep could not judge yet — %s"
                    % str(_unmeasured[0].get("why"))[:170], k=_atkK, n=_atkN)
    if not rows:
        # ⚠ v2847 — THE ZERO CARRIES ITS DENOMINATOR. "Nothing busy and old" was a clean-looking 0
        # with nothing behind it: it could not be told from a sweep that scanned nothing, used a
        # bar nothing could clear, or asked once and caught a quiet moment. This line is what he
        # reads when he wants to know the machine is clear, and on 2026-09-09 he asked exactly that
        # while a single CPU sample had me about to end his console. Say what was measured.
        #
        # ⚠⚠ EVERY WORD HERE IS CHOSEN TO AVOID A LIST THIS MODULE MAY NOT CONTAIN.
        # `test_health_engine.test_the_module_writes_nothing` scans this file for the names of
        # process-ending and file-destroying calls, because health_engine REPORTS and never
        # REPAIRS — his rule, and the reason is that an auto-healer turns one fault into two
        # unattended. The scan is a CAPABILITY check and is right to be blunt.
        #
        # ⚠ AND MY FIRST FIX FOR IT FAILED THE SAME LAW A SECOND WAY: rewriting this comment to
        # explain the ban, I spelled out the very tokens the ban lists, and the gate refused again
        # naming a different one. A note about a forbidden vocabulary must not speak it.
        # Describe the capability; never name the call. [[feedback-comments-vs-code]]
        # [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
        # ⚠ #171 (REG-2482) — THE DENOMINATOR COMES FROM THE SWEEP THAT JUST RAN, AND IT NAMES ITS INSTRUMENT.
        # This used to take a SECOND `ps` sample only to count it: one more process-table read per tick on a Mac, and
        # on Windows - no ps - a count of UNKNOWN printed beside a clean verdict. last_scan() is what suspects()
        # itself measured a moment ago, and by what. None = no sweep measured, never "zero processes".
        try:
            _scan = MO.last_scan() or {}
        except Exception:
            _scan = None
        _n = (_scan or {}).get("n")
        _how = (_scan or {}).get("how") or "an instrument that did not say which"
        _ports = (_scan or {}).get("portsSay") or (
            "Processes on his ports (%s) and their children are excluded by name, never counted as mine."
            % ", ".join(":%d" % p for p in MO.HIS_PORTS))
        return _row("orphans", OK,
                    "nothing busy and old that is not a known system process — %s process(es) "
                    "scanned by %s, bar %.0f%% sustained and %d min old. %s"
                    % ("UNKNOWN" if _n is None else _n, _how, MO.BUSY_PCT, MO.OLD_MIN, _ports),
                    k=_atkK, n=_atkN)

    # ⚠⚠ v2744 — TWO ANSWERS, NOT ONE, AND THE OLD ONE CLAIMED SOMETHING IT NEVER TESTED.
    # This row said "nothing of OURS is both busy and old" while `my_orphans` had no ownership test
    # at all — `ppid` was parsed and never read, and the only filter was a substring list that
    # flagged `coreaudiod`, `ControlCenter` and PID 1. `.console_scars.json.corrupt` records eight
    # earlier false positives of the same kind. Worse, WARN maps to MISSING on the rail, so a
    # system daemon rendered as the rail's FAILURE state.
    #
    # Now attribution travels with each row and the two are graded differently:
    #   OURS          -> WARN. Something I started is burning a core. Actionable, and mine.
    #   UNATTRIBUTED  -> UNKNOWN. Busy and old and nobody can say whose. That is genuinely
    #                   unknown, and UNKNOWN is the state this repo has for exactly that.
    # ⚠ UNATTRIBUTED IS NOT DISMISSED. Today's real runaway — 100% CPU for 52 minutes — was in no
    # spawn ledger, named no tree path and held no port; all three positive witnesses failed on it.
    # A rule that only reported POSITIVE ownership would have said nothing about it at all.
    # [[unknown-stays-unknown]] [[i-own-everything-i-start]]
    #
    # ⚠ #171 (REG-2482, the review of the first cut) — SAY ONLY WHAT WAS ASKED. This sentence claimed all three
    # witnesses for EVERY row that is not ours: "not in the spawn ledger, not naming this tree, holding none of our
    # ports". That is true of a row the attribution answered None — every witness was asked and none could say. A
    # row it answered False (NEVER MINE) stopped at his ports: it is on one, under his console, or its port could not
    # be read — and on Windows, with no lsof, that is EVERY row, so the line claimed three checks that never ran
    # about the console's own capture and a prover that names this tree. Each class now says what was established
    # about it, in the attribution's own words. [[unknown-stays-unknown]] [[feedback-comments-vs-code]]
    def _fmt(r):
        _w = str(r.get("whose") or "") if r.get("ours") is False else ""
        return "pid %s %.0f%% CPU %.0f min — %s%s" % (r.get("pid"), r.get("cpu", 0), r.get("minutes", 0),
                                                      str(r.get("cmd"))[:70], (" — " + _w[:110]) if _w else "")

    def _not_ours(rs):
        _never, _nobody = [], []
        for r in rs:
            (_never if r.get("ours") is False else _nobody).append(r)
        _say = []
        if _never:
            _why = []
            for r in _never:
                _w = str(r.get("whose") or "NEVER MINE").split("NEVER MINE — ", 1)[-1].strip()
                if _w not in _why:
                    _why.append(_w)
            _say.append("%d never counted as mine — %s%s; the spawn ledger and this tree were not asked"
                        % (len(_never), _why[0][:170],
                           (" (+%d other reason(s), each in the list)" % (len(_why) - 1)) if len(_why) > 1 else ""))
        if _nobody:
            _say.append("%d where nothing can say whose they are — not in the spawn ledger, not naming this tree, "
                        "holding none of our ports" % len(_nobody))
        return "; ".join(_say)
    mine = [r for r in rows if r.get("ours") is True]
    unattributed = [r for r in rows if r.get("ours") is not True]
    if mine:
        return _row("orphans", WARN,
                    "%d process(es) OF OURS busy and old%s"
                    % (len(mine),
                       ("; %d more busy and old, none of them ours: %s" % (len(unattributed), _not_ours(unattributed)))
                       if unattributed else ""),
                    [_fmt(r) for r in mine] + [_fmt(r) for r in unattributed], k=_atkK, n=_atkN)
    return _row("orphans", UNKNOWN,
                "%d process(es) busy and old, and none can be called ours: %s. UNATTRIBUTED is not the same as "
                "ours, and not the same as fine." % (len(unattributed), _not_ours(unattributed)),
                [_fmt(r) for r in unattributed], k=_atkK, n=_atkN)


def check_self_arming():
    """★ v2438 — THE LOCKS THAT UNLOCK THEMSELVES, REPORTING INTO THE HEART.

    Konyo, 2026-09-02: *"connect everything to the heart of the console, it should all be
    communicating"* — so the lock does not get its own private endpoint. It reports here, the
    eagle publishes it, and every surface QUOTES one source. That is v2436's lesson applied
    forward: two surfaces deriving one number is how the panel and the server disagreed.

    ⚠ THE STATE MAPPING IS THE WHOLE CARE HERE. A lock that has never been sabotaged is
    UNPROVEN, and UNPROVEN IS NOT A FAULT — it is work not yet done. Painting it WARN would turn
    the newest surfaces amber and the mechanism would be ignored inside a week ([[heart-first]]).
    So unproven reports OK with an honest line; only an UNREADABLE queue is UNKNOWN, and only a
    lock that was tested and could not refuse is WARN.
    """
    try:
        import self_arming as SA
    except Exception as e:
        return _row("selfArming", UNKNOWN, "the lock module will not import — %s" % str(e)[:70])
    try:
        rep = SA.report()
    except Exception as e:
        return _row("selfArming", UNKNOWN, "the locks could not be read — %s" % str(e)[:70])
    if not rep.get("ok"):
        return _row("selfArming", UNKNOWN,
                    "the proof queue could not be read, so no lock may open — %s"
                    % rep.get("why", ""))
    locks = rep.get("locks") or []
    # REG-3215 - each lock's evidence line leads with the ACT word ("shut - the prover is behind · proven 0.90 >= 0.72"),
    # never "OPEN" over a lock that may not act; a row from an older report with no words keeps its state word.
    ev = ["%s: %s — %s" % (l.get("lock"),
                           ("%s · %s" % (l.get("actSay"), l.get("provenSay") or "")) if l.get("actSay")
                           else l.get("state"), l.get("why", "")) for l in locks]
    # A route earns trust in a number. It is not a valve, and the old tally counted it as a
    # lock. HARDENED is earned open, the same pair the heart badge already uses. This row
    # was the second copy, and it counted OPEN only, so a hardened shelf read as none open.
    valves = [l for l in locks if l.get("kind") != "route"]
    routes = [l for l in locks if l.get("kind") == "route"]
    # REG-1950 — A ROUTE IS NOT A LOCK HERE EITHER. The OK line below counts valves and routes apart, while
    # this list and the score ran over EVERY row: a route that did not refuse was reported as "a lock that did
    # not refuse", and a route's trials sat in the lock score (the #231 eye on 2f5cb714). Each keeps its own word.
    inert = [l for l in valves if l.get("state") == SA.LOCKED]
    inert_routes = [l for l in routes if l.get("state") == SA.LOCKED]
    unproven = [l for l in valves if l.get("state") == SA.UNPROVEN]
    incomplete = [l for l in valves if l.get("state") == SA.INCOMPLETE]
    # ⚠⚠ v3093 — THE TALLY IS COMPUTED BEFORE THE BRANCHES, BECAUSE IT USED TO REACH ONLY ONE.
    # `k=tot_k, n=tot_n` were passed on the OK return and on NEITHER of the others. So the moment a
    # lock actually went inert — the finding this check exists to make — the row lost its proofK,
    # its proofN and its score entirely, and `_row` computes the Wilson number only when `n` is not
    # None. MEASURED on his live console: health_engine's selfArming row was `warn` and carried NO
    # k, NO n and NO score key at all, while heart.vessels() reported FLOWING: None with the reason
    # "no organ row carries a score for any watcher". The scorer was alive and only ever ran on the
    # happy path.
    #
    # The proof history does not depend on the verdict. A lock that was sabotaged forty times and
    # refused thirty-eight has that history whether today's answer is OK, WARN or UNKNOWN, and the
    # heart needs it most precisely when something is wrong. [[the-unjoined-end]]
    # [[zero-needs-a-denominator]]
    tot_k = sum(int(l.get("k") or 0) for l in valves)
    tot_n = sum(int(l.get("n") or 0) for l in valves)
    if inert or inert_routes:
        # tested, and could not refuse. THAT is the finding — a guard that cannot say no.
        worst = (inert or inert_routes)[0]
        ev = [("%s: %s — %s" % (worst.get("lock"), worst.get("state"), worst.get("why", "")))] \
             + [e for e in ev if not e.startswith("%s:" % worst.get("lock"))]
        said = []
        if inert:
            said.append("%d lock(s) were sabotaged and did not refuse" % len(inert))
        if inert_routes:
            said.append("%d route(s) were sabotaged and did not refuse" % len(inert_routes))
        return _row("selfArming", WARN,
                    "%s — %s" % (" · ".join(said), worst.get("lock")), ev, k=tot_k, n=tot_n,
                    surfaces=[l.get("lock") for l in locks if l.get("lock")])

    # ⚠ DERIVED, NOT DECLARED: the surfaces are the locks this row actually judged, taken from
    # the same list its evidence is built from. A declaration beside the function could drift
    # from what it reads; this cannot.
    # A missing or blind heart means may() is refusing. A stale census is the prover lagging
    # the code, which is not a verdict about these locks, so it is named and the row stays OK.
    # REG-3215 - THE ACT QUESTION LEADS. This said "7 of 9 locks open" - the evidence tier - while 4 of the 9 may
    # act; the count is self_arming's one tally, the same sentence the heart prints: "4 of 9 may act now (7 proven)".
    parts = [SA.lock_counts(valves)["say"]]
    if incomplete:
        parts.append("%d incomplete (an axis nobody could exercise, not a fault)"
                     % len(incomplete))
    parts.append("%d still unproven (nobody has tried to break them yet, "
                 "which is work owed and not a fault)" % len(unproven))
    if routes:
        route_open = sum(1 for r in routes if r.get("state") in (SA.OPEN, SA.HARDENED))
        parts.append("%d of %d routes proven" % (route_open, len(routes)))
    line = " · ".join(parts)
    heart_why = str(rep.get("heartWhy") or "")
    heart_shut = (not rep.get("heartOk") and SA.heart_block_kind(heart_why) != "stale")
    state = OK
    if heart_shut:
        state = UNKNOWN
        line = "%s — none of that may act here: %s" % (
            line, heart_why or "the heart refused and gave no reason")
    elif heart_why and not rep.get("heartOk"):
        line = "%s — %s" % (line, heart_why)
    return _row("selfArming", state, line,
                ev, k=tot_k, n=tot_n,
                surfaces=[l.get("lock") for l in locks if l.get("lock")])

#: One walk of the gate roster, memoised on the ledger's mtime. See `_attack_tally`.
_ATK_CACHE = {"key": None, "per_file": None}
#: #172 (2026-10-27) - ONE PARSE PER GATE FILE, NOT ONE PER CENSUS CHANGE. MEASURED on a private console booted on a copy of
#: his tree: the attack tally ast.parses every gate file's RED_PROOF list (~1,100 files) each time the census store moves -
#: and the self-prover moves it every slice - so the console re-parsed the whole suite again and again, and the parse's
#: freed C arenas stay resident (the ALT's console holds 1.28 GB private). A file's RED_PROOF list depends on that file's
#: bytes alone, so each is kept per file and re-read only when the file's size or mtime moved. Replaced in ONE binding
#: per file (control_app is threaded); an unreadable file is not cached - it is asked again next time.
_RP_FILE_CACHE = {}


def _red_proofs_cached(h2, fn):
    """heart2.red_proofs_in(fn), kept per gate file until its size or mtime moves. -> list | None"""
    try:
        st = os.stat(os.path.join(h2.HERE, fn))
        key = (st.st_mtime_ns, int(st.st_size))
    except OSError:
        return h2.red_proofs_in(fn)
    hit = _RP_FILE_CACHE.get(fn)
    if hit is not None and hit[0] == key:
        return hit[1]
    got = h2.red_proofs_in(fn)
    if got is not None:
        _RP_FILE_CACHE[fn] = (key, got)
    return got


_LANE_SPAN_CACHE = {"key": None, "val": None}


def _lane_spans():
    """The console's watcher lanes and where each one's code actually lives.

    ⚠ MEMOISED ON control_app.py's OWN stat, because parsing 19k lines costs ~260 ms and this is
    called on every health report — which his console renders on a timer. Keyed on (mtime_ns,
    size) so an edit re-parses and nothing is ever served from a stale tree. Not a TTL: there is
    no interval to guess and no window where the answer is wrong. [[stale-reading]]
    -> {fn_name: (lane, first_line, last_line)}

    ⚠ PARSED FROM THE REGISTRY, NEVER A LIST HERE. control_app.py pairs every lane name with the
    function that runs it in one (name, fn) table; a copy in this file is a second source that
    goes stale the first time a lane is renamed. [[copy-drift]] [[source-reading-guard]]
    """
    _p = os.path.join(HERE, "control_app.py")
    with io.open(_p, encoding="utf-8") as _fh:
        _src = _fh.read()
        _st = os.fstat(_fh.fileno())        # the handle actually read, never a second stat
    _key = (_st.st_mtime_ns, int(_st.st_size))
    _snap = _LANE_SPAN_CACHE
    if _snap.get("key") == _key and _snap.get("val") is not None:
        return _snap["val"], _src
    # #172 phase B - A CONSOLE NEVER PARSES ITS OWN 49k LINES IN ITS OWN HEAP. The ast of control_app.py is ~930k objects
    # and its freed arenas stay resident; a console reads the answer a short-lived child derived (audit_child.py), keyed
    # on the same stat, and derives here only when the child could not (fails open, and the doctor says so).
    try:
        import audit_child as _ac
        if _ac.wanted():
            _got = _lane_spans_disk(_key)
            if _got is not None:
                _ac.hit("lane_spans")
            else:
                _ac.run("lane_spans")
                _got = _lane_spans_disk(_key)
            if _got is not None:
                globals()["_LANE_SPAN_CACHE"] = {"key": _key, "val": _got}
                return _got, _src
    except Exception:
        pass
    import ast as _ast
    _tree = _ast.parse(_src)
    _lanes = {}
    for _n in _ast.walk(_tree):
        if (isinstance(_n, _ast.Tuple) and len(_n.elts) == 2
                and isinstance(_n.elts[0], _ast.Constant)
                and isinstance(_n.elts[0].value, str)
                and _n.elts[0].value.startswith("tvd-")
                and isinstance(_n.elts[1], _ast.Name)):
            _lanes[_n.elts[1].id] = _n.elts[0].value
    out = {}
    for _n in _ast.walk(_tree):
        if isinstance(_n, _ast.FunctionDef) and _n.name in _lanes:
            out[_n.name] = (_lanes[_n.name], _n.lineno, _n.end_lineno or _n.lineno)
    globals()["_LANE_SPAN_CACHE"] = {"key": _key, "val": out}   # ONE binding: control_app is threaded
    return out, _src


def _lane_spans_cache_path():
    """#172 phase B - where the lane spans a child derived are kept: beside the route census's own cache, so a fixture
    world keeps both in its own root and never in his tree. -> path | None"""
    try:
        import chronicle_routes as _cr
        return os.path.join(_cr._routes_cache_root(), ".lane_spans_cache.json")
    except Exception:
        return None


def _lane_spans_disk(key):
    """The lane spans a child wrote for this exact stat of control_app.py, else None. -> {fn: (lane, a, b)} | None"""
    p = _lane_spans_cache_path()
    if not p:
        return None
    try:
        with io.open(p, encoding="utf-8") as fh:
            blob = json.load(fh) or {}
        if blob.get("key") != [int(key[0]), int(key[1])] or not isinstance(blob.get("val"), dict):
            return None
        return {str(k): (str(v[0]), int(v[1]), int(v[2])) for k, v in blob["val"].items()}
    except Exception:
        return None


def _attribute_to_lanes(hits):
    """Which WATCHER LANE each sabotage actually struck. -> {lane: (k, n)}

    ⚠⚠ PER LANE, NEVER PER FILE — this is the whole point and the easy way to get it wrong.
    MEASURED: 163 RED_PROOFs name control_app.py and only 6 of them land inside one of the twelve
    watcher loops. Crediting every lane with the file's tally would publish FLOWING 20/20 out of
    evidence that never touched nine of them. An n inflated by REPETITION is fake confluence, and
    a heart that overstates its own supervision is worse than one that admits the gap.
    So a proof counts for a lane only when its `find` lands INSIDE that lane's def span.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """
    per = {}
    if not hits:
        return per
    try:
        spans, src = _lane_spans()
    except Exception:
        return per
    for _proven, _ran, _single, _find in hits:
        if not _find:
            continue
        _i = src.find(_find)
        if _i < 0:                       # a dead anchor strikes nothing and earns nothing
            continue
        _ln = src.count("\n", 0, _i) + 1
        for _fn, (_lane, _a, _b) in spans.items():
            if _a <= _ln <= _b:
                k, n = per.get(_lane, (0, 0))
                if _proven:
                    per[_lane] = (k + 1, n + 1)
                elif _ran and _single:
                    per[_lane] = (k, n + 1)
                break
    return per


def _attack_rollup():
    """Attacks per PROOF FILE, from one walk of the roster. -> ({file: (k, n)} , ok)

    ⚠⚠⚠ v3139 — THE TALLY COST 1,020 ms A CALL AND THE CHEAP SUBSET RUNS IT TWICE. MEASURED after
    v3138: one `_attack_tally()` = 1020 ms, three organs = 2265 ms per health pass, and
    `test_the_cheap_subset_is_actually_CHEAP` blocked the push at 10,062 ms against a 9,000 ms
    budget — a path that runs at EVERY console boot. Walking 368 gates and AST-parsing each, three
    times over, for an answer that changes only when the ledger or a gate file changes.

    ⚠ THE GATE CAUGHT A REAL REGRESSION I SHIPPED. `heart-first` says build the organ WITH the
    thing; it does not say make his console boot 2.3s slower to do it. [[poll-slower-than-its-interval]]

    So: ONE walk, keyed on `.heart2.json`'s mtime+size and the roster's own fingerprint, rolled up
    per proof FILE so every hint is answered from the same pass. A stale key simply recomputes;
    nothing is served from a cache that cannot prove it is current. [[stale-reading]]
    """
    try:
        import json as _json
        import heart2 as _h2
        _sp = os.path.join(HERE, ".heart2.json")
        _st = os.stat(_sp)
        with io.open(_sp, encoding="utf-8") as fh:
            _store = _json.load(fh) or {}
        # ⚠⚠⚠ v3140 — THE KEY MUST COVER WHAT THE WALK READS, AND v3139's DID NOT. It keyed on
        # `.heart2.json` alone while the walk PARSES LIVE GATE SOURCE for every RED_PROOF's `file`.
        # Repoint a proof from my_orphans.py to lane_liveness.py without re-proving and the ledger
        # never moves: the organ keeps publishing the old k/n — including `score: 0.0` = INERT if
        # that is what the stale tuple held. And `_ATK_CACHE` is PROCESS-LIFETIME and never
        # cleared, so his running console would hold that answer until it restarts.
        # `console_doctor.py` already recorded this shape and forbade it: share for ONE TICK, never
        # as a process-lifetime memo, because a later caller gets the previous answer.
        #
        # MEASURED: `gate_files()` + `os.stat` on all 368 sources is 7 ms against a 1,020 ms walk —
        # under 1% — so the key can cover the real inputs exactly, with no TTL to guess and no
        # window where a stale answer is served. `st_mtime_ns`, not `int(st_mtime)`: a second's
        # truncation left byte-size as the only real invalidator for a ledger edit.
        # [[stale-reading]] [[zero-needs-a-denominator]]
        # ⚠⚠⚠ v3141 — XOR CANCELS, AND ONE FILE IS LISTED TWICE. v3140 folded the roster with
        # `_sig ^= mtime_ns ^ (size << 1)`, which is a fingerprint of TERMS, not of files: any
        # path `gate_files()` yields an EVEN number of times contributes exactly NOTHING, and
        # `_cnt` counts both visits so it does not save you. MEASURED: the roster is 368 entries
        # over 367 distinct files, and `lane_census.py` appears TWICE — so editing that one file
        # could never move the key, and the v3140 High it was written to close stayed open for it.
        # A sorted digest over (path, mtime_ns, size) cannot cancel and does not care about order.
        # [[zero-needs-a-denominator]]
        _seen = {}
        for _gn, _gf in _h2.gate_files(say=lambda *a, **k: None):
            _rel = str(_gf)
            if _rel in _seen:
                continue
            try:
                _gs = os.stat(os.path.join(HERE, _rel))
            except Exception:
                _seen[_rel] = (None, None)
                continue
            _seen[_rel] = (_gs.st_mtime_ns, _gs.st_size)
        _digest = _hashlib.sha1(
            repr(sorted(_seen.items())).encode("utf-8", "replace")).hexdigest()
        # ⚠ AND control_app.py, because the per-LANE rollup below attributes a proof by the
        # DEF SPAN it lands in. Edit that file and every span moves; a key blind to it would keep
        # publishing attacks credited to whichever lane used to own those lines.
        _ca = os.stat(os.path.join(HERE, "control_app.py"))
        _key = (_st.st_mtime_ns, int(_st.st_size),
                str(_store.get("gatesFingerprint") or ""), len(_seen), _digest,
                _ca.st_mtime_ns, int(_ca.st_size))
    except Exception:
        return None, False
    # ⚠ v3141 — SNAPSHOT, BECAUSE THE READER HAD THE WINDOW TOO. v3140 replaced the dict in one
    # binding on the WRITE side and left the READ as two lookups: a writer swapping the dict
    # between them returns the NEW payload against the OLD key's test. One local reference is what
    # "one binding" actually requires.
    _snap = _ATK_CACHE
    if (_snap.get("key") == _key and _snap.get("per_file") is not None
            and _snap.get("per_lane") is not None):
        return _snap["per_file"], True
    _proved = set(_store.get("provedGates") or [])
    _ran = _proved | set(_store.get("blind") or [])
    per, _ca_hits = {}, []
    try:
        for _name, _fn in _h2.gate_files():
            _proofs = _red_proofs_cached(_h2, _fn) or []   # #172 - one parse per gate file until it changes
            if not _proofs:
                continue
            _files = {str(_p.get("file") or "") for _p in _proofs}
            _single = len(_files) == 1
            for _p in _proofs:
                if "control_app" in str(_p.get("file") or ""):
                    _ca_hits.append((_name in _proved, _name in _ran, _single,
                                     str(_p.get("find") or "")))
            for _f in _files:
                _mine = sum(1 for _p in _proofs if str(_p.get("file") or "") == _f)
                k, n = per.get(_f, (0, 0))
                if _name in _proved:
                    per[_f] = (k + _mine, n + _mine)   # proven ⇒ each went red ⇒ each a refusal
                elif _name in _ran and _single:
                    per[_f] = (k, n + 1)               # ONE gate, ONE failed attempt
    except Exception:
        return None, False
    # ⚠ v3140 — ONE ASSIGNMENT, NOT TWO. `_ATK_CACHE["key"], _ATK_CACHE["per_file"] = ...` is two
    # STORE_SUBSCRs, and between them the dict reads {new key, OLD per_file}. control_app is
    # THREADED — the eagle timer and a request can both be in here — so a reader hitting that gap
    # publishes the previous gate's k/n under the new ledger's identity. Replacing the module dict
    # in a single binding closes the window in CPython.
    globals()["_ATK_CACHE"] = {"key": _key, "per_file": per,
                               "per_lane": _attribute_to_lanes(_ca_hits)}
    return per, True


def _attack_tally(*module_hints):
    """Sabotages fired at the lane-liveness machinery, and how many earned a refusal. -> (k, n)

    ⚠⚠ v3135 (#80) — WITHOUT THIS, NOT ONE OF THE 20 VESSELS COULD EVER REACH FLOWING. MEASURED
    on his live console: `heart.vessels()` returned 20 WATCHED, `FLOWING: None`, every row reading
    "watched, and NOTHING CAN SCORE THIS WATCHER YET. No organ publishes a score." `heart.py`
    defines FLOWING as "it runs, something watches it, AND A SABOTAGE HAS PROVEN THE WATCHER CAN
    REFUSE", and `_row` computes the Wilson number only when `n` is not None. This organ passed
    neither k nor n, so score stayed None — UNPROVEN — for every thread it watches.

    ⚠ THE DENOMINATOR IS SABOTAGES ATTEMPTED, NEVER AGREEMENTS. Counting runs-that-passed would
    make the score rise precisely because nothing was ever tested, which is the failure the
    self-arming lock doctrine exists to prevent.

    ⚠ AND IT READS ATTACKS THAT ACTUALLY RAN, rather than starting a second attack engine beside
    heart2. Every RED_PROOF whose `file` is the lane-liveness module is a sabotage declared
    against this machinery; heart2's store records which gates went red under theirs. MEASURED:
    n=2, k=2 — `test_a_lane_with_no_period_can_still_go_red` and
    `test_a_tick_filed_under_a_lane_name_still_counts`, both PROVEN.

    ⚠ DERIVED, NEVER A FROZEN LIST. Naming the two gates here is how a tuple goes stale the moment
    a third arrives — twice today that exact shape was the defect. [[copy-drift]]

    -> (None, None) when the record cannot be read, because an unreadable ledger is UNKNOWN and
    must never stand as "zero attacks". [[zero-needs-a-denominator]]
    """
    per, ok = _attack_rollup()
    if not ok or per is None:
        return None, None
    k = n = 0
    for _f, (_k, _n) in per.items():
        if any(h in _f for h in module_hints):
            k += _k
            n += _n
    return (k, n) if n else (None, None)

def check_lane_liveness():
    """Which THREADS this watchdog can see beat, named one by one. -> row

    ⚠⚠ v3046 — IT WATCHED TWENTY AND THE ORGAN TABLE SAID IT NAMED THREE. Measured on his live
    console: all 20 vessels carry a watcher with `via: lane_liveness`, so this organ genuinely
    covers every one of them — and organ_matrix still counted 15 as "named by NO organ", because
    every row here describes a SUBSYSTEM (lanes, readers, orphans) rather than the individual
    threads. Real supervision, unnamed, and therefore invisible to the table whose whole job is
    asking who covers what. [[the-unjoined-end]]

    ⚠ DERIVED FROM SOURCE, NOT FROM `_TICKS`. That dict is PROCESS MEMORY — rich inside
    control_app, EMPTY everywhere else — so a row built from it would name twenty surfaces on his
    console and none in any gate or matrix run. A parse of who calls `_lane_tick('name')` answers
    the same question from anywhere, and "anywhere" is where this table is read.
    [[feedback-suspect-the-instrument]]
    """
    # ⚠⚠ v3135 — COMPUTED BEFORE THE BRANCHES, BECAUSE ITS SIBLING ALREADY PAID FOR THAT.
    # v3093 on `selfArming`: "`k=tot_k, n=tot_n` were passed on the OK return and on NEITHER of
    # the others. So the moment a lock actually went inert — the finding this check exists to
    # make — the row lost its proofK, its proofN and its score entirely." The proof history does
    # not depend on today's verdict: a watcher sabotaged twice and refused twice has that history
    # whether this run says OK, WARN or UNKNOWN, and the heart needs it most when something is
    # wrong. [[the-unjoined-end]] [[zero-needs-a-denominator]]
    _atkK, _atkN = _attack_tally("lane_liveness")
    try:
        import lane_liveness as _ll
        m = _ll.stamping_functions()
    except Exception as e:
        return _row("laneLiveness", UNKNOWN,
                    "the liveness reader would not load — %s" % str(e)[:70], k=_atkK, n=_atkN)
    failed = m.get("__failed__") if isinstance(m, dict) else None
    if failed:
        return _row("laneLiveness", UNKNOWN,
                    "the lanes could not be read from source (%s), so which threads this "
                    "watchdog can see is UNKNOWN rather than none" % str(failed)[:60],
                    k=_atkK, n=_atkN)
    fns = sorted(k for k in m if k != "__failed__")
    if not fns:
        return _row("laneLiveness", WARN,
                    "no function in the console stamps a lane, so nothing here can be seen to "
                    "beat at all", k=_atkK, n=_atkN, surfaces=[])
    ev = ["%s -> %s" % (k, ", ".join(m[k])) for k in fns[:12]]
    return _row("laneLiveness", OK,
                "%d thread(s) stamp a lane this watchdog can read · %s"
                % (len(fns),
                   ("%d of %d sabotage(s) against this watchdog earned a refusal"
                    % (_atkK, _atkN)) if _atkN else
                   "NO sabotage has been fired at this watchdog yet — work owed, not a fault"),
                ev, k=_atkK, n=_atkN, surfaces=fns)


def check_shelf_witnesses():
    # ⚠ v3135 (#80) — the same join as laneLiveness: attacks that ACTUALLY RAN against
    # this organ's own module, read from heart2's record. Computed BEFORE the branches so
    # a bad verdict cannot cost the row its proof history. [[the-unjoined-end]]
    _atkK, _atkN = _attack_tally("shelf_corroborate")
    """Is the shelf being WITNESSED at all? -> row

    ⚠ THIS IS NOT THE CORROBORATOR'S QUESTION AND MUST NOT BECOME IT. Whether the witnesses
    AGREE is `shelf_corroborate`'s verdict and it has its own organ. A watchdog asks whether
    the thing is alive: can the shelf be read, is any reel still witnessable, did the organ
    actually run. Collapsing the two would leave the shelf with one organ wearing two hats,
    which is exactly the coverage illusion organ_matrix exists to refuse.

    ⚠ ZERO WITNESSABLE REELS IS NOT HEALTH. A shelf with no film on disk cannot be
    corroborated by anything, so a clean-looking "0 disagreements" would be a verdict with no
    denominator. That case reports WARN with the count beside it.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    try:
        import shelf_corroborate as _sc
    except Exception as e:
        return _row("shelfWitness", UNKNOWN,
                    "the shelf corroborator could not be loaded (%s), so nothing is witnessing "
                    "the shelf — unknown, not clear" % type(e).__name__, k=_atkK, n=_atkN)
    try:
        rep = _sc.report()
    except Exception as e:
        return _row("shelfWitness", UNKNOWN,
                    "the shelf corroborator raised %s, so its reading is UNKNOWN"
                    % type(e).__name__, k=_atkK, n=_atkN)
    # ⚠⚠ v3233 — "COULD NOT ASK" AND "ASKED AND FOUND NONE" ARE DIFFERENT FACTS, AND THIS READ
    # THEM THE SAME. `rep.get("checked") or 0` turns BOTH a real 0 and an UNKNOWN into 0, so a
    # console that is down produced "0 reel(s) on disk could be witnessed" — a WARN about the
    # shelf, when the true statement is that nothing could look at it. Film can sit under
    # frames/hist the whole time. v3231 added `sessionsUnknown` to say so and NOTHING READ IT:
    # the flag and its only consumer were built at opposite ends and never joined, which a
    # cross-family review of that very version caught. [[the-unjoined-end]] [[unknown-stays-unknown]]
    if rep.get("sessionsUnknown") or rep.get("checked") is None:
        return _row("shelfWitness", UNKNOWN,
                    str(rep.get("unknownWhy") or rep.get("say")
                        or "the shelf corroborator could not be asked, so its reading is UNKNOWN"),
                    evidence={"checked": None, "disagreed": None}, k=_atkK, n=_atkN)
    checked = rep.get("checked") or 0
    bad = rep.get("disagreed") or 0
    if not checked:
        return _row("shelfWitness", WARN,
                    "0 reel(s) on disk could be witnessed, so the shelf is UNCORROBORATED — "
                    "that is unmeasured, not agreement",
                    evidence={"checked": 0, "disagreed": 0}, k=_atkK, n=_atkN)
    if bad:
        return _row("shelfWitness", WARN,
                    "%d of %d witnessable reel(s) disagree with themselves about their own "
                    "frame count — the shelf is watched and it is reporting a contradiction"
                    % (bad, checked),
                    evidence={"checked": checked, "disagreed": bad}, k=_atkK, n=_atkN)
    return _row("shelfWitness", OK,
                "%d witnessable reel(s), every one agreeing across dossier, card and disk"
                % checked,
                evidence={"checked": checked, "disagreed": 0}, k=_atkK, n=_atkN)


def check_read_lanes_at_cap():
    """A vision lane sitting at its ceiling — refusing every read while looking merely idle.

    ⚠⚠ THE FAILURE THIS EXISTS FOR, MEASURED THE DAY IT WAS WRITTEN. The GROK lane had recorded
    201 calls against a _DAILY_MAX of 200, so `g5_grok_eyes._budget_ok()` returned False on EVERY
    call and the lane read nothing at all. Nothing said so: the console's meter showed only the
    Claude lane, and the Grok Bot had been posting "Quartz ON-SCREEN none — seat EMPTY" tick after
    tick. An exhausted lane and an un-toggled lane produce the identical silence, and only one of
    them is a fault. [[zero-needs-a-denominator]] [[the-unjoined-end]]

    OFF IS NOT A FAULT. A lane he has not switched on is reported OK — the watchdog's job is to
    catch a lane that MEANS to work and cannot, not to nag about a switch he chose.
    """
    try:
        import control_app as _ca
        lanes = (_ca._meter_state() or {}).get("lanes") or {}
    except Exception as e:
        return _row("read_lanes_at_cap", UNKNOWN,
                    "the read meter could not be asked (%s), so whether a lane is capped is "
                    "UNMEASURED rather than fine" % e)
    if not lanes:
        return _row("read_lanes_at_cap", UNKNOWN,
                    "the meter returned no lanes at all — it used to report a single lane and a "
                    "reader that finds none cannot say the lanes are healthy")
    capped, unknown = [], []
    for name, v in sorted(lanes.items()):
        if not isinstance(v, dict):
            continue
        if v.get("atCap") is None:
            unknown.append(name)
        elif v.get("atCap") and v.get("on"):
            # ⚠ v3098 — THE WINDOW THAT TRIPPED, NOT ALWAYS THE DAILY ONE. This formatted
            # `day`/`dailyMax` unconditionally while `atCap` is true if EITHER window is full, so
            # an hour at 4000/4000 printed "(4000 of 20000 today) is AT ITS CEILING" — a correct
            # number under a word that had stopped being true, on the one line whose whole job is
            # to say there is no headroom. `capText` is computed once in control_app._cap_state
            # and says which window. [[label-outlived-referent]] [[zero-needs-a-denominator]]
            capped.append("%s (%s)" % (name, v.get("capText")
                                       or "at its ceiling, window UNKNOWN"))
    if capped:
        return _row("read_lanes_at_cap", WARN,
                    "%s is AT ITS CEILING and is refusing every read — which looks exactly like a "
                    "lane nobody switched on, and is not the same fact" % "; ".join(capped))
    if unknown:
        return _row("read_lanes_at_cap", UNKNOWN,
                    "could not measure the ceiling for: %s" % ", ".join(unknown))
    return _row("read_lanes_at_cap", OK,
                "%d read lane(s) measured, none at its ceiling" % len(lanes))


_RECEIPT_CACHE = {"key": None, "val": None}


def _receipt_hooks():
    """Does the VAULT emit the hooks the receipt viewer reads? -> dict

    ⚠ MEMOISED ON bible.html's OWN stat. That file is ~6 MB and the health report runs on his
    console's timer; re-reading it every tick is the shape that made /api/heart cost 20s.
    """
    _p = os.path.join(os.path.dirname(HERE), "bible.html")
    try:
        _st = os.stat(_p)
    except Exception:
        return {"ok": False}
    _key = (_st.st_mtime_ns, int(_st.st_size))
    _snap = _RECEIPT_CACHE
    if _snap.get("key") == _key and _snap.get("val") is not None:
        return _snap["val"]
    try:
        with io.open(_p, encoding="utf-8") as _fh:
            _src = _fh.read()
    except Exception:
        return {"ok": False}
    _val = {"ok": True}
    # v3168 - the REMOVAL DOOR's tokens ride along in this same read. bible.html is ~6 MB and a
    # second organ opening it again per tick is the shape that made /api/heart cost 20 s, so both
    # vault organs ask one reader. The door is DRIVEN end-to-end in node by
    # test_the_removal_door_is_undoable.py; this count only answers "is it still on the page",
    # which is a presence question a count can honestly answer. [[source-reading-guard]]
    # ⚠⚠ v3180 — IT WAS COUNTING THE CONSOLE'S CLASSES INSIDE THE BOARD'S FILE. MEASURED:
    # `rc-art` and `rcpt-ic` appear 6 and 5 times in tv/control_ui.html and ZERO times in
    # bible.html — they are the CONSOLE's receipt viewer. The BOARD has its own, and always did:
    # `tvd-frame-thumb` (5) with `_tvdOpenFrame` (7). The vault renders on the BOARD, so those are
    # the hooks a vault row would have to emit.
    #
    # So check_vault_receipts has been reporting "the vault emits NO receipt hook at all" from a
    # premise that could never come true, in an organ I wrote and shipped. The vault genuinely
    # does not emit them — that part stands — but the row was proving it against the wrong file,
    # which means it would ALSO have said "absent" on the day the join landed.
    # A guard that cannot go green is as useless as one that cannot go red.
    # [[feedback-suspect-the-instrument]] [[copy-drift]]
    for _k in ("tvd-frame-thumb", "_tvdOpenFrame", "data-frame",
               "window.vaultRemove = function", "window.vaultRestoreLast = function",
               "d2r_vaultRemoved", "window.vaultRemove([name]"):
        _val[_k] = _src.count(_k)
    globals()["_RECEIPT_CACHE"] = {"key": _key, "val": _val}
    return _val


def _vault_row_has_frame():
    """Does the VAULT ROW itself carry a frame hook? -> bool

    ⚠ NOT "is a viewer present on the page". bible.html has shipped `tvd-frame-thumb` for
    versions, for the AI-reads strip — so a page-wide count reads as JOINED while every vault row
    is still bare. The question is whether the row builder emits it, so this reads the row markup
    between its own anchors rather than counting the file. [[source-reading-guard]]
    """
    _p = os.path.join(os.path.dirname(HERE), "bible.html")
    try:
        with io.open(_p, encoding="utf-8") as _fh:
            _src = _fh.read()
    except Exception:
        return False
    _a = _src.find('return \'<div class="vrg-row"')
    if _a < 0:
        return False
    _b = _src.find("</div>';", _a)
    if _b < 0:
        return False
    _row = _src[_a:_b]
    # the row's receipt hook: `data-rcpt` carries the item NAME, and the delegated handler asks
    # /api/evidence for it on click. Either that, or the board's own frame thumb if a future
    # version embeds one directly — both mean "this row can show what witnessed it".
    return ("data-rcpt" in _row) or ("tvd-frame-thumb" in _row) or ("data-frame" in _row)


def _receipt_resolution_clause(rres):
    """The sentence for how many receipts can OPEN, and whether that is a broken address. -> (str, bool)

    ONE wording for both paths of check_vault_receipts (#123 — the no-backup early return had none,
    and a second copy of this sentence is how the two would drift). [[copy-drift]]
    """
    if rres[1] and rres[0] == 0:
        # every banked frame unreachable is a BROKEN ADDRESS, not pruned footage: pruning takes
        # frames one at a time and never lands on exactly all of them.
        return ("; and NOT ONE of the %d banked best-frames opens where the board looks - the "
                "receipt button is wired to an address nothing lives at" % rres[1]), True
    if rres[1]:
        return ("; %d of %d banked best-frames still have their footage on disk (the rest were "
                "pruned, which is honest absence rather than a broken link)" % rres), False
    return ("; whether those receipts can actually OPEN is UNKNOWN - the evidence bank could not "
            "be read here"), False


def _receipts_resolve(sample=None):
    """Of the banked best-frames, how many can the board ACTUALLY open? -> (resolved, tested)

    ⚠ v3182 — THIS EXISTS BECAUSE THE ROW ABOVE WAS GREEN OVER A JOIN THAT NEVER ONCE WORKED.
    _vault_row_has_frame() asks whether the receipt BUTTON is in the row markup. It was, so the
    organ said "ok". Measured 2026-09-15: the button resolved 4 of 450 banked best-frames,
    because the handler threw the reel away and every lookup addressed a FLAT hist/<ms>.jpg while
    evidence frames live at hist/reel_<sid>/f_<ms>.jpg. Presence is not resolution, and a health
    check that cannot tell them apart will certify a dead feature forever.
    [[the-green-that-lies]] [[the-unjoined-end]]

    Returns (resolved, tested). tested is 0 when the bank cannot be read - the caller must then
    say UNKNOWN, never 0. [[zero-needs-a-denominator]]
    """
    # ⚠ import json HERE. The module-level `_json` is None until another function imports it
    # locally, so `_json.load` raised AttributeError, the bare except swallowed it, and this
    # returned a clean-looking (0, 0) - a wrong zero inside the very helper written to stop a
    # wrong zero. The denominator is what caught it. [[zero-needs-a-denominator]]
    import json as _j
    _bank = os.path.join(HERE, "chron_evidence.json")
    _hist = os.path.join(HERE, "frames", "hist")
    try:
        with io.open(_bank, encoding="utf-8") as _fh:
            _b = _j.load(_fh)
    except Exception:
        return 0, 0
    _best = {}
    for _sec in ("uniques", "sets"):
        for _n, _rows in (_b.get(_sec) or {}).items():
            _bst = None
            for _r in (_rows or []):
                if not isinstance(_r, dict) or not _r.get("frame"):
                    continue
                if not _bst or (_r.get("conf") or 0) > (_bst.get("conf") or 0):
                    _bst = _r
            if _bst:
                _best[_n] = _bst
    _names = list(_best.items())
    if sample:
        _names = _names[:int(sample)]
    _ok = 0
    for _n, _r in _names:
        _reel = _r.get("reel")
        if not _reel:
            continue
        if os.path.isfile(os.path.join(_hist, str(_reel), str(_r.get("frame")))):
            _ok += 1
    return _ok, len(_names)


def check_vault_receipts(backup_dir=None):
    """Can he SEE why a vault row is there? -> row

    ⚠⚠ HIS ASK, AND HE WAS RIGHT THAT SOMETHING WAS BUILT. The console already carries the whole
    receipt apparatus: a cursor-following frame float on `.rc-art`, a full-HD viewer on the
    `.rcpt-ic` eye reading the real on-disk /hist/<frameId>.jpg, and a route-to-source click. The
    evidence store already records `{reel, frame, lane}` per sighting.

    What has never existed is the INTRODUCTION. The vault emits NONE of those hooks, so an item in
    a locker cannot show the frame that witnessed it. Built, correct, and joined to nothing — the
    same shape as the pixel witness before v2912 put it on the wire. [[the-unjoined-end]]

    ⚠ AND THE COUNT IS THE POINT. MEASURED: 172 owned, 153 filed into lockers, ZERO carrying a
    sighting. An item with no receipt looks identical to one with a reel behind it, which is how
    150 rows from a retired found-ever backfill sat in his lockers looking exactly like finds.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    _atkK, _atkN = _attack_tally("health_engine")
    import glob as _glob
    import json as _json
    # ⚠ a SEAM, so a law can drive an empty dir and an unreadable backup instead of waiting
    # for his real one to be in the right state. An organ no law can drive is one no law tests.
    _dir = backup_dir or os.path.expanduser("~/d2r_ledger_backups")
    try:
        _files = sorted(_glob.glob(os.path.join(_dir, "ledger_*.json")))
    except Exception:
        _files = []
    def _resolution_only(why):
        # ⚠ #123 — RESOLUTION DOES NOT NEED THE BACKUP. Whether a receipt can OPEN is a question about
        # banked frames on disk. ⚠ AND BOTH EARLY RETURNS GO THROUGH HERE: v3490 measured it for the
        # empty directory, and the corrupt-backup return still skipped it and passed no evidence, so
        # the one fact the row exists for vanished whenever the backup would not parse, and a bank
        # where nothing opens could not grade WARN (the second eye on v3490, grok-4.7). One helper,
        # so neither door can skip it again. [[copy-drift]]
        try:
            _rr0 = _receipts_resolve()
        except Exception:
            _rr0 = (0, 0)
        _clause0, _broken0 = _receipt_resolution_clause(_rr0)
        return _row("vaultReceipts", WARN if _broken0 else UNKNOWN, why + _clause0,
                    evidence=[("receiptFrames %d of %d open on disk" % _rr0) if _rr0[1]
                              else "receiptFrames UNKNOWN (the bank could not be read)"],
                    k=_atkK, n=_atkN)
    if not _files:
        return _resolution_only("no ledger backup exists yet, so nothing here can say how many vault "
                                "rows carry a receipt - which is not the same as saying none do")

    try:
        with io.open(_files[-1], encoding="utf-8") as _fh:
            _b = _json.load(_fh)
        _a = _b.get("allStores") or {}
        _owned = _json.loads(_a.get("d2r_owned") or "[]")
        _mule = _json.loads(_a.get("d2r_muleAssign") or "{}")
        _ev = _json.loads(_a.get("d2r_foundEvidence") or "{}")
    except Exception as _e:
        return _resolution_only("the newest ledger backup could not be read (%s), so the receipt "
                                "count is UNKNOWN rather than zero" % type(_e).__name__)
    # ⚠⚠ v3180 — d2r_foundEvidence IS NOT THE EVIDENCE BANK. It holds EIGHT rows in his backup and
    # none of them are owned items, so this reported "0 of 172 carry a sighting" — a figure that is
    # true of that store and FALSE of the system. The real bank is tv/chron_evidence.json: 324
    # uniques and 126 sets carrying 8,517 sightings, and asking /api/evidence for all 172 owned
    # names returns REEL SIGHTINGS WITH FRAMES for 147 of them, 111 at conf >= 0.90.
    #
    # That wrong 0 is what made "remove everything with no evidence" look like a 129-item job when
    # the honest answer is 18. A number measured from the wrong store does not become safe by
    # being printed confidently.
    # [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
    _bank = {}
    try:
        with io.open(os.path.join(HERE, "chron_evidence.json"), encoding="utf-8") as _bf:
            _cb = _json.load(_bf)
        for _sec in ("uniques", "sets"):
            _d = _cb.get(_sec)
            if isinstance(_d, dict):
                _bank.update(_d)
    except Exception:
        _bank = {}

    # ══ v3183 — THE ORGAN AND THE ROUTE MUST ASK THE SAME QUESTION ════════════════════════
    # control_app.evidence_for now resolves by VAULT ENTITY (item_identity), so a row whose
    # evidence is banked under a typographic apostrophe, a base-type tail, or an unambiguous
    # "(set piece)" suffix finds it. If this organ kept doing an exact dict-get, the console
    # would open a receipt for a row this row had just counted as unwitnessed - two organs
    # disagreeing about one number, which is the failure the vault_bank reader exists to stop.
    # [[copy-drift]]
    try:
        import item_identity as _ii
    except Exception:
        _ii = None
    _bank_by_entity = {}
    if _ii is not None:
        for _k, _v in _bank.items():
            _ssk = _v if isinstance(_v, list) else (
                (_v or {}).get("sightings") if isinstance(_v, dict) else None)
            if _ssk:
                _bank_by_entity.setdefault(_ii.vault_key(_k).lower(), True)

    def _has_sighting(_n):
        _v = _bank.get(_n)
        _ss = _v if isinstance(_v, list) else ((_v or {}).get("sightings") if isinstance(_v, dict) else None)
        if _ss:
            return True
        # ⚠ ENTITY, NOT BYTES - and the qualifier still separates Latent from Renewed, so this
        # never lends one Sunder Charm's footage to another.
        if _ii is not None and _bank_by_entity.get(_ii.vault_key(_n).lower()):
            return True
        _l = _ev.get(_n)          # the thin local store still counts when it has one
        return isinstance(_l, dict) and bool(_l.get("sightings"))

    _withev = [n for n in _owned if _has_sighting(n)]
    _hooks = _receipt_hooks()
    # ⚠ THE JOIN IS "does a VAULT ROW carry a frame", not "does the page contain a viewer".
    # bible.html has carried tvd-frame-thumb for versions — for the AI-reads strip, not the vault
    # — so counting the viewer alone would have read as joined while every vault row stayed bare.
    # The vault's own row markup is what has to change, and `_vault_row_has_frame()` asks that.
    _joined = bool(_hooks.get("ok") and _vault_row_has_frame())
    _line = ("%d of %d owned row(s) carry a sighting; %d are filed into a locker"
             % (len(_withev), len(_owned), len(_mule)))
    if not _joined:
        _line += ("; and the vault emits NO receipt hook at all, so even a row that HAS a frame "
                  "cannot show it - the viewer and the evidence have never been introduced")
    # ══ v3182 — A RECEIPT THAT CANNOT OPEN IS NOT A RECEIPT ═══════════════════════════════
    # `_joined` above asks whether the row carries a receipt HOOK. That was true, and this row
    # said "ok", while the hook resolved 4 of 450 banked frames - it addressed a flat
    # hist/<ms>.jpg and the frames live at hist/reel_<sid>/f_<ms>.jpg. Presence and resolution
    # are different questions and only one of them is the feature. [[the-green-that-lies]]
    _rres = _receipts_resolve()
    _state = OK if (_joined and _withev) else (WARN if _owned else UNKNOWN)
    _clause, _broken = _receipt_resolution_clause(_rres)
    _line += _clause
    if _broken:
        _state = WARN
    return _row("vaultReceipts", _state, _line,
                # ⚠ A LIST, NOT A DICT. `_row` does `list(evidence or [])`, so a dict lands as
                # its KEY NAMES and every number is lost. v3145's check_lane_attacks has been
                # publishing ['proven','inert','neverAttacked','perLane'] — four labels and no
                # figures — since it shipped. A field that silently drops what you put in it is
                # worse than one that refuses. [[zero-needs-a-denominator]]
                evidence=["owned %d" % len(_owned), "filed %d" % len(_mule),
                          "withSighting %d" % len(_withev),
                          # v3182 — RESOLUTION, not presence. See _receipts_resolve.
                          ("receiptFrames %d of %d open on disk" % _rres) if _rres[1]
                          else "receiptFrames UNKNOWN (the bank could not be read)",
                          # ⚠ v3193 — NAME THE TOKENS ACTUALLY COUNTED. v3182 changed
                          # _receipt_hooks to look for the board's own viewer hooks and left this
                          # label saying rc-art / rcpt-ic, which are no longer measured — so the
                          # line read "rc-art=None" forever. Worse, the law that grades this row
                          # guards its assertions on "rc-art=0" and therefore stopped running them
                          # entirely: green while examining nothing, which is the one failure the
                          # heart exists to catch. [[label-outlived-referent]]
                          "hooks %s" % (" ".join("%s=%s" % (k, v) for k, v in
                                                 sorted((_hooks or {}).items())
                                                 if k != "ok") or "none measured"),
                          "backup %s" % os.path.basename(_files[-1])],
                k=_atkK, n=_atkN, surfaces=["vault-receipts"])


def check_lane_attacks():
    """Which of the console's twelve watcher LANES has ever been sabotaged, and refused. -> row

    ⚠⚠ #80 — THIS IS THE HALF heart.vessels() COULD NOT REACH. Twelve vessels sat at WATCHED with
    `score: None` because NO organ row named a single `tvd-*` lane in its surfaces, and a vessel
    inherits its score from the organ that names it. Not scored low — unscorable, forever.

    ⚠⚠ THE SCORE PUBLISHED IS THE WEAKEST NAMED LANE'S, NOT THE SUM. Summing the three proven
    lanes gives (6, 6) -> 0.6097 and would credit each of them with the other two's sabotages;
    every named lane really has (2, 2) -> 0.3424. Since `heart.scored` hands one row's score to
    every surface it names, the only number that overstates nobody is the MINIMUM. A surface is
    as proven as ITS OWN evidence. [[unknown-stays-unknown]]

    ⚠ AND A LANE THAT WAS ATTACKED AND NEVER REFUSED IS NOT NAMED AT ALL. Publishing it here
    would hand it the group's earned score; it is a WARN in the line instead, because `score: 0.0`
    means INERT and that claim belongs to the lane that earned it, not to its neighbours.
    """
    per, ok = _attack_rollup()
    _lanes = (_ATK_CACHE.get("per_lane") if ok else None)
    try:
        _all = sorted(set(l for (l, _a, _b) in _lane_spans()[0].values()))
    except Exception:
        _all = []
    if not ok or _lanes is None or not _all:
        return _row("laneAttacks", UNKNOWN,
                    "the sabotage ledger or the lane registry could not be read, so nothing is "
                    "known about who has ever attacked the console's watcher lanes - which is "
                    "not the same as nobody having attacked them")
    _proven = sorted(l for l, (k, n) in _lanes.items() if k > 0)
    _inert = sorted(l for l, (k, n) in _lanes.items() if n > 0 and k == 0)
    _never = sorted(l for l in _all if l not in _lanes)
    # ⚠⚠ THE WEAKEST LANE, NOT THE WEAKEST NUMERATOR AND THE WEAKEST DENOMINATOR. The second eye
    # on v3145 caught this and it reproduces: min(k) and min(n) taken INDEPENDENTLY can invent a
    # pair no lane actually holds. Lane A (2,5) and lane B (2,2) -> componentwise (2,2) -> 0.3424,
    # while A's own evidence supports 0.1176. A three-fold overstatement, published by the very
    # organ written to refuse overstatement. Today every lane is (2,2) so the two agree — which is
    # exactly why the law drives it instead of reading the live ledger.
    # [[unknown-stays-unknown]] [[gate-blind-to-unexercised-input]]
    import confidence as _conf                   # one home for the maths — never a copy
    _weak = min(_proven,
                key=lambda l: _conf.wilson_lower(_lanes[l][0], _lanes[l][1])) if _proven else None
    _k, _n = _lanes[_weak] if _weak else (None, None)
    line = ("%d of %d watcher lane(s) have earned a refusal under sabotage (weakest %s/%s, and "
            "that is the score published so none is credited with another's proof)"
            % (len(_proven), len(_all), _k, _n))
    state = OK
    if _inert:
        state = WARN
        line += "; %d ATTACKED AND NEVER REFUSED: %s" % (len(_inert), ", ".join(_inert))
    if _never:
        state = WARN if _inert else UNKNOWN
        line += ("; %d have never been attacked at all, so they are UNMEASURED rather than "
                 "clean: %s" % (len(_never), ", ".join(_never)))
    return _row("laneAttacks", state, line,
                # ⚠ v3167 — THIS WAS A DICT AND `_row` KEPT ONLY THE KEYS. Shipped in v3145, it
                # published ['proven','inert','neverAttacked','perLane'] — the lane names and
                # their k/n never reached the payload at all.
                evidence=(["proven: " + (", ".join(_proven) or "none")]
                          + (["INERT: " + ", ".join(_inert)] if _inert else [])
                          + (["never attacked: " + ", ".join(_never)] if _never else [])
                          + ["%s k=%d n=%d" % (l, _lanes[l][0], _lanes[l][1])
                             for l in sorted(_lanes)]),
                k=_k, n=_n, surfaces=_proven,
                # each lane carries ITS OWN number: the row-wide weakest is the honest answer only
                # while nothing better is known, and here something better IS known.
                surface_scores=dict(
                    (l, _conf.wilson_lower(_lanes[l][0], _lanes[l][1])) for l in _proven))


def check_vault_removals(backup_dir=None):
    """Is every removal from his vault dated, listed and UNDOABLE? -> row

    HIS ORDER, 2026-09-15: *"Build a removal door - a board-side vault_remove(names[]) with the
    same care as chronicleApply: dated, listed, undoable, and stamped once... connect it to the
    heart of the console so its tracked."*

    WHAT THIS WATCHES. #96 has to take ~150 backfilled names out of `d2r_owned`. Until v3168 the
    only board-side remover was `vaultUnown(name)`: one name, no record, and an undo that lived
    only in his memory. v3168 added the batch door AND routed the one-click path through it, so
    every removal on the board is journaled to `d2r_vaultRemoved` (a ring of 20 batches).

    THE ZERO HERE HAS A DENOMINATOR, AND IT IS NOT THE OBVIOUS ONE. An empty journal means
    "nothing removed SINCE THE DOOR SHIPPED" - never "nothing was ever removed", because every
    removal before v3168 left no trace at all. This row says which of the two it is measuring,
    because a bare 0 beside the word "removals" would be read as the stronger claim.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]

    AND IT WATCHES THE JOIN, NOT JUST THE DOOR. If the one-click path ever stops routing through
    vaultRemove, single removals go back to leaving no record while the batch count still looks
    healthy - the failure would be INVISIBLE in a row that only counted batches.
    [[the-unjoined-end]]
    """
    _atkK, _atkN = _attack_tally("health_engine")
    import glob as _glob
    import json as _json
    _h = _receipt_hooks()
    _door = bool(_h.get("ok") and _h.get("window.vaultRemove = function")
                 and _h.get("window.vaultRestoreLast = function"))
    _routed = bool(_h.get("ok") and _h.get("window.vaultRemove([name]"))
    if not _door:
        return _row("vaultRemovals", WARN,
                    "the board has no removal door - items can still be taken out of the vault, "
                    "but nothing records what left or lets him put it back",
                    evidence=["door: absent from bible.html"], k=_atkK, n=_atkN)
    _dir = backup_dir or os.path.expanduser("~/d2r_ledger_backups")
    try:
        _files = sorted(_glob.glob(os.path.join(_dir, "ledger_*.json")))
    except Exception:
        _files = []
    if not _files:
        return _row("vaultRemovals", UNKNOWN,
                    "the removal door is on the board, but no ledger backup exists yet - so "
                    "whether anything has been removed is UNKNOWN, not zero",
                    evidence=["door: present", "one-click routed: %s" % _routed],
                    k=_atkK, n=_atkN)
    try:
        with io.open(_files[-1], encoding="utf-8") as _fh:
            _b = _json.load(_fh)
        _a = _b.get("allStores") or {}
        _raw = _a.get("d2r_vaultRemoved")
        _log = _json.loads(_raw) if _raw else []
        if not isinstance(_log, list):
            _log = []
    except Exception as _e:
        return _row("vaultRemovals", UNKNOWN,
                    "the newest ledger backup could not be read (%s), so the removal journal is "
                    "UNKNOWN rather than empty" % type(_e).__name__,
                    evidence=["door: present"], k=_atkK, n=_atkN)
    _names = sum(len(_x.get("names") or []) for _x in _log if isinstance(_x, dict))
    _newest = None
    for _x in _log:
        if isinstance(_x, dict) and _x.get("day"):
            _newest = _x.get("day")
    _ev = ["door: present, undo: present",
           "one-click path routed through the door: %s" % _routed,
           "batches in the journal: %d (the ring caps at 20)" % len(_log),
           "names removed through the door: %d" % _names,
           "newest batch: %s" % (_newest or "none"),
           "read from: %s" % os.path.basename(_files[-1])]
    _state = OK
    if not _log:
        _line = ("the removal door is live and nothing has been removed through it yet - a real "
                 "zero for removals SINCE v3168, not a claim about anything removed before it")
    else:
        _line = ("%d name(s) removed from the vault across %d journaled batch(es), newest %s - "
                 "every one of them still undoable" % (_names, len(_log), _newest or "undated"))
    if not _routed:
        _line += ("; but the one-click un-own no longer routes through the door, so single "
                  "removals are leaving no record beside the batches")
        _state = WARN
    return _row("vaultRemovals", _state, _line, evidence=_ev, k=_atkK, n=_atkN)


def check_stash_bank():
    """Is the backend bank that feeds the vault actually being fed? -> row

    HIS ORDER, 2026-09-15: *"all information that can be extracted should be backend tallied
    regardless of the ledger.. like there should be a backend ledger already architured"* — and
    *"fix the gaps for everything else and connect it to the heart of the console all 4 organs"*.

    HE WAS RIGHT THAT IT EXISTS, and it was starved. Two banks, same idea, opposite health:
        chron_evidence.json   324 uniques · 8517 sightings · 262 refusals kept on purpose
        vault_accum (the stash bank)   12 keys
    MEASURED: the sweeper read reels in DIRECTORY ORDER filtered only by "not already sealed", so
    it spent 45 sessions on arbitrary footage (36 of them, 80%, took nothing) while the three best
    stash-panel reels — one at 100% density — had never been swept. The ranking existed and was
    computed only inside a doctor row that PRINTS it. v3171 joined it to the sweeper.

    ⚠ THIS ROW WATCHES THE FEED, NOT THE VAULT. check_vault_receipts asks whether a vault row can
    show its evidence; check_vault_removals asks whether removals are journaled. Neither could see
    that the thing SUPPLYING the evidence had stopped taking anything — which is why 18 vault rows
    have nothing behind them and nobody noticed. [[the-unjoined-end]]

    ⚠ ONE READER for all four organs. [[copy-drift]]
    """
    _atkK, _atkN = _attack_tally("health_engine")
    try:
        import vault_bank as _vb
        _w, _line = _vb.headline()
        _st = _vb.state()
    except Exception as _e:
        return _row("stashBank", UNKNOWN,
                    "the stash bank could not be read (%s), so its yield is UNKNOWN rather than "
                    "zero" % type(_e).__name__, k=_atkK, n=_atkN)
    _ev = ["sweeps: %s took something of %s" % (_st.get("yieldedN"), _st.get("sweptN")),
           "examined and honestly empty: %s" % _st.get("silentN"),
           "recorded NO reason (UNKNOWN, not empty): %s" % _st.get("noReasonN"),
           "rows banked: %s" % _st.get("rowsBanked"),
           "accumulator keys: %s" % _st.get("accumKeys"),
           "vault_seen rows: %s (%s carry a frame, %s at zero confidence)"
           % (_st.get("seenRows"), _st.get("seenWithFrame"), _st.get("seenZeroConf")),
           "chronicle bank for scale: %s sighting(s) over %s name(s)"
           % (_st.get("chronSightings"), _st.get("chronUniques"))]
    _state = {"OK": OK, "WARN": WARN}.get(_w, UNKNOWN)
    return _row("stashBank", _state, _line, evidence=_ev, k=_atkK, n=_atkN)


def check_sweep_meter():
    """Can he SEE the read he is paying for? -> row

    HIS ASK, 2026-09-15: *"time meter for the sweep i want included integrated and installed so I
    can see it in th esticky tab console section on the right nder the fleet"*.

    WHAT THIS WATCHES, AND WHY A GATE CANNOT. The gate
    (test_the_sweep_says_how_long_it_has_been_reading) pins the CODE: that vault_sweep_state calls
    sweep_eta, in reels, and that the meter is started. All of that can be true while the thing he
    actually asked for is still absent, because a sweep started by a process that predates the run
    clock carries no `runStartedTs` at all - and that is not hypothetical. It is exactly the state
    this console was in while the meter was being built: a live vault read 65.6 minutes in, 119
    paid reads and 309 pages spent, running inside an interpreter that had never heard of the
    clock. The gate was green for that whole hour. A gate fails when code changes; a heart says a
    thing is unsupervised even when nobody touched it. [[join-gate-heart]]

    THE THREE STATES IT DISTINGUISHES, because collapsing them is the failure:
      - no sweep running            -> ok, and says so. Not a zero.
      - running WITH a clock        -> ok, and prints the elapsed time it can see.
      - running WITHOUT a clock     -> WARN. He is spending money against a blind meter.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    _atkK, _atkN = _attack_tally("control_app")
    try:
        import control_app as _ca
    except Exception as _e:
        return _row("sweepMeter", UNKNOWN,
                    "the console module would not import, so whether the sweep meter can see a "
                    "read is unmeasured - not healthy, unknown",
                    evidence=["import control_app: %s" % type(_e).__name__],
                    k=_atkK, n=_atkN)
    try:
        st = _ca.vault_sweep_state() or {}
    except Exception as _e:
        return _row("sweepMeter", WARN,
                    "the sweep state could not be read, so the meter in the rail has nothing to "
                    "draw: %s" % str(_e)[:80],
                    evidence=["vault_sweep_state raised %s" % type(_e).__name__],
                    k=_atkK, n=_atkN)

    eta = st.get("eta") or {}
    # ⚠ NAME THE VENUE. _VAULT_JOB is per-PROCESS. Run inside the console this row is about the
    # sweep he can see; run standalone from a gate it is about a module imported five seconds ago
    # that has obviously never swept anything - and those two produce the SAME cheerful "no read
    # in flight". Measuring in the wrong process has already cost this session one confident wrong
    # answer, so the row carries its own pid rather than implying it speaks for the console.
    ev = ["eta key present: %s" % ("yes" if "eta" in st else "NO"),
          "phase: %s" % (st.get("phase") or "?"),
          "running: %s" % bool(st.get("running")),
          "measured in pid %d (the vault job is per-process)" % os.getpid()]

    if "eta" not in st:
        return _row("sweepMeter", WARN,
                    "the vault sweep publishes no estimate at all - the meter he asked for has "
                    "nothing to render, and a read can run for an hour unseen",
                    evidence=ev, k=_atkK, n=_atkN)

    if not st.get("running"):
        _last = st.get("lastRunMs")
        ev.append("last run recorded: %s" % ("yes" if _last else "no"))
        return _row("sweepMeter", OK,
                    "no vault read is in flight; the meter is wired and showing %s"
                    % ("what the last one cost" if _last
                       else "that nothing has run since this console started"),
                    evidence=ev, k=_atkK, n=_atkN)

    _el = eta.get("elapsedMs")
    ev.append("elapsedMs: %r" % _el)
    ev.append("runStartedTs: %r" % st.get("runStartedTs"))
    if not _el:
        # ⚠ THE CASE THIS ROW EXISTS FOR. A read is burning subscription calls and the meter
        # cannot say for how long. Measured live on 2026-09-15 for at least 65.6 minutes.
        return _row("sweepMeter", WARN,
                    "a vault read is RUNNING and the meter cannot say for how long - this "
                    "console was started before the run clock existed, so restart it to put a "
                    "time on the next read",
                    evidence=ev, k=_atkK, n=_atkN)

    _mins = round(float(_el) / 60000.0, 1)
    ev.append("reels: %s of %s" % (st.get("runReelsDone"), st.get("runReelsTotal")))
    ev.append("paid reads this run: %s" % st.get("classified"))
    return _row("sweepMeter", OK,
                "a vault read is running and the meter can see it - %s minute(s) elapsed, %s"
                % (_mins, eta.get("say") or "size not yet known"),
                evidence=ev, k=_atkK, n=_atkN)


def check_input_latency():
    """The last click-to-paint sample on the board.

    No beat is UNKNOWN. A missing p95 is not 0. A number over the v3769
    budget is WARN. A long task the observer has not seen stays absent and
    does not read as a zero-length task.
    """
    try:
        import input_latency as IL
    except Exception as e:
        return _row("inputLatency", UNKNOWN, "input latency could not be loaded - %s" % e)
    sample = IL.read()
    if not isinstance(sample, dict):
        return _row("inputLatency", UNKNOWN, "has not reported an input latency yet")
    p95, mx, n = sample.get("p95"), sample.get("maxLongtask"), sample.get("n")
    ev = ["p50=%s" % sample.get("p50"), "p95=%s" % p95,
          "maxLongtask=%s" % mx, "n=%s" % n]
    if IL.P95_BUDGET_MS is None or IL.LONGTASK_BUDGET_MS is None:
        return _row("inputLatency", UNKNOWN,
                    "the v3769 latency budget has not been entered", evidence=ev)
    if not isinstance(p95, (int, float)) or isinstance(p95, bool):
        if isinstance(mx, (int, float)) and not isinstance(mx, bool) and mx > IL.LONGTASK_BUDGET_MS:
            return _row("inputLatency", WARN,
                        "longest task %.0f ms is over the v3769 budget of %.0f ms, and no click has been sampled"
                        % (mx, IL.LONGTASK_BUDGET_MS), evidence=ev)
        return _row("inputLatency", UNKNOWN, "has not reported an input latency yet", evidence=ev)
    over = []
    if p95 > IL.P95_BUDGET_MS:
        over.append("p95 %.0f ms over %.0f" % (p95, IL.P95_BUDGET_MS))
    if isinstance(mx, (int, float)) and not isinstance(mx, bool) and mx > IL.LONGTASK_BUDGET_MS:
        over.append("longest task %.0f ms over %.0f" % (mx, IL.LONGTASK_BUDGET_MS))
    if over:
        return _row("inputLatency", WARN,
                    "input latency is over the v3769 budget - " + "; ".join(over),
                    evidence=ev)
    if mx is None:
        line = ("click-to-paint p95 %.0f ms (n=%s), no long task reported, inside the v3769 budget"
                % (p95, n))
    else:
        line = ("click-to-paint p95 %.0f ms, longest task %.0f ms, inside the v3769 budget"
                % (p95, mx))
    return _row("inputLatency", OK, line, evidence=ev)


CHECKS = [check_lanes, check_read_lanes_at_cap, check_armed_migrations, check_board_join, check_orphans,
          check_input_latency,
          check_shelf_witnesses,
          check_shadow_watch, check_readers_agree, check_self_arming,
          check_lane_liveness, check_lane_attacks, check_vault_receipts,
          check_vault_removals, check_stash_bank, check_sweep_meter]


def report(evaluate=None, board=None):
    """Every flag, in one object. `board` is a /api/board_ownership payload. -> dict"""
    rows = []
    for fn in CHECKS:
        try:
            rows.append(fn(evaluate, board) if fn is check_board_join else fn())
        except Exception as e:                                   # a check that throws is UNKNOWN
            rows.append(_row(getattr(fn, "__name__", "?"), UNKNOWN,
                             "this check raised and therefore measured nothing — %s" % e))
    worst = OK
    for r in rows:
        if r["state"] == BLOCKED:
            worst = BLOCKED; break
        if r["state"] in (WARN, UNKNOWN) and worst == OK:
            worst = r["state"]
    return {"state": worst, "rows": rows,
            "why": "; ".join(r["line"] for r in rows if r["state"] != OK) or "everything measured is fine"}


GLYPH = {OK: "🟢", WARN: "🟡", BLOCKED: "🔴", UNKNOWN: "⚪"}


def say(rep):
    return ["%s %-18s %s" % (GLYPH.get(r["state"], "·"), r["id"], r["line"]) for r in rep["rows"]]


def main(argv=None):
    rep = report()
    for line in say(rep):
        print("   " + line)
    print()
    print({OK: "🟢 nothing is asking for you.",
           WARN: "🟡 something wants a look.",
           BLOCKED: "🔴 something downstream cannot proceed.",
           UNKNOWN: "⚪ something could not be measured — that is not the same as fine."}[rep["state"]])
    return 0 if rep["state"] == OK else 1


if __name__ == "__main__":
    import sys
    try:
        sys.path.insert(0, HERE)
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
