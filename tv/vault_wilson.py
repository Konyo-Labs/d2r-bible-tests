"""A2 · can the VAULT APPLY refuse when it must? (vault.forget has its own harness: vault_forget_wilson.py)

`vault.apply` guards "mules items between characters": the door that WRITES HIS LEDGER. Its bar is
0.722 and it sat UNPROVEN at n=0 because nothing was permitted to feed it.

⚠⚠ THIS HARNESS NEVER APPLIES ANYTHING. Every attempt is a proposal the door MUST reject, and each
one is rejected at the re-gate — v1595's check — which returns BEFORE the board is ever asked. The
only thing counted is whether it refused. There is no attempt here whose success path runs.

⚠ THE ROWS ARE BUILT TO FAIL. Each carries an EMPTY evidence list, so `vault_retro.gate()` refuses
it on witnesses alone. A row that might pass would be a row that might be written into his stash,
and that is not a risk a test may take. [[feedback-fixtures-never-touch-live-data]]

⚠⚠ HISTORY, RETRACTED BY REG-3819 (11-13): the paragraph below was true until the ledger drop gained its refusal.
`vault.forget` is now attacked by vault_forget_wilson.py. What it said then: CANNOT BE PROVEN THIS WAY AT ALL. Measured by
AST — 7 lines, one return, and ZERO refusal paths. It clears the swept memory and always answers
ok. Its own docstring explains why that is correct: "an optimisation he cannot clear is a cage",
and the ledger is rebuildable from the reels. So there is no wrong input for it to catch, and its
lock will sit UNPROVEN forever — not because nobody tried, but because there is nothing to try.
That is a fact about the door, not a gap in the evidence, and inventing a sabotage for it would be
manufacturing proof. [[unknown-stays-unknown]]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _ungated_proposal(n_rows=1):
    """A proposal whose rows carry NO evidence — guaranteed to fail the witness gate."""
    return {"owned": [{"name": "SABOTAGE ROW %d — no evidence, must never be written" % i,
                       "evidence": []} for i in range(n_rows)],
            "unsure": [], "throwOut": []}


def _attempt_ungated(ca, n=8):
    """v1595's re-gate: a hand-supplied proposal is re-checked WHERE THE WRITE HAPPENS."""
    caught = 0
    for i in range(n):
        r = ca.vault_apply(proposal=_ungated_proposal(1 + (i % 3)))
        if isinstance(r, dict) and r.get("ok") is False and "gate" in str(r.get("why", "")).lower():
            caught += 1
    return n, caught


def _attempt_empty(ca, n=8):
    """An empty proposal must not be treated as 'apply whatever the sweep last found'."""
    caught = 0
    for _ in range(n):
        r = ca.vault_apply(proposal={"owned": [], "unsure": [], "throwOut": []})
        if isinstance(r, dict) and r.get("ok") is False:
            caught += 1
    return n, caught



# ══ v3067 — FOUR ATTACKS DESIGNED BY A DIFFERENT MODEL FAMILY ═══════════════════════════════
# `vault_apply` was handed COLD — comments stripped, no premise — to the third eye, the same
# method that found the `unsure` hole in v2641. It returned five payloads and had run them.
# FOUR of the five were LIVE against the shipped code; every one is now refused.
#
# ⚠ THESE ARE FOUR DISTINCT MECHANISMS, NOT ONE IDEA IN FOUR COATS, and that distinction is the
# whole arithmetic: self_arming scores on wilson_lower(min(k, attacks), attacks), so looping one
# attack buys nothing. They fail at four different joints — the container, the row, the type
# check, and an ungated lane.
# ⚠ NOTHING REACHES HIS LEDGER. Each attempt runs with the board eval stubbed, and a refusal
# never reaches the window at all.

def _stub_board():
    """Return (restore_fn, sent) — the board's eval replaced by a recorder."""
    import control_app as ca
    sent = {}
    real = (getattr(ca, "_ejs", None), ca.__dict__.get("_BOARD_WIN"), ca.__dict__.get("_WINDOW_LIVE"))

    def _fake(w, js, timeout=8.0):
        sent["js"] = js
        return '{"ok":true,"applied":{}}'

    ca._ejs = _fake
    ca._BOARD_WIN = object()
    ca._WINDOW_LIVE = True

    def restore():
        if real[0] is not None:
            ca._ejs = real[0]
        ca._BOARD_WIN, ca._WINDOW_LIVE = real[1], real[2]
    return restore, sent


# #246 W3 (2026-09-26): a look counts as a witness only with its OWN frame and conf over the floor, so the decoy's
# looks carry frames. Without them the decoy row was refused, the WHOLE proposal fell, and throwout-evidence read
# "caught 0 of 6" - the door was right, the instrument had stopped reaching the lane it probes. [[feedback-suspect-the-instrument]]
_CLEAN_EV = [{"session": "s%d" % i, "witness": "s%d#0" % i, "frame": "s%d/f0001.png" % i, "conf": 0.9} for i in range(3)]
_DIRTY = {"name": "SABOTAGE Shako — no evidence, must never be written", "lane": "stash",
          "kind": "item", "count": 1, "evidence": []}


def _leaked(ca, proposal, needle):
    restore, sent = _stub_board()
    try:
        ca.vault_apply(proposal=proposal)
        return needle in (sent.get("js") or "")
    finally:
        restore()


def _attempt_poison_row(ca, n=6):
    """A ROW that lies about its own evidence — .get() answers the gate once, stores nothing."""
    class PoisonRow(dict):
        def get(self, k, default=None):
            if k in ("evidence", "witnesses") and not getattr(self, "_fed", False):
                self._fed = True
                return list(_CLEAN_EV)
            return dict.get(self, k, default)
    caught = 0
    for _ in range(n):
        prop = {"ok": True, "owned": [PoisonRow({"name": "SABOTAGE Poison Shako",
                                                 "lane": "stash", "kind": "item", "count": 1})],
                "unsure": [], "throwOut": []}
        if not _leaked(ca, prop, "SABOTAGE Poison Shako"):
            caught += 1
    return n, caught


def _attempt_flip_container(ca, n=6):
    """A CONTAINER that answers the gate and the write differently."""
    class FlipList(list):
        def __iter__(self):
            if not getattr(self, "_g", False):
                self._g = True
                return iter([{"name": "decoy", "lane": "stash", "kind": "rune", "count": 1,
                              "evidence": list(_CLEAN_EV)}])
            return list.__iter__(self)
    caught = 0
    for _ in range(n):
        prop = {"ok": True, "owned": FlipList([dict(_DIRTY)]), "unsure": [], "throwOut": []}
        if not _leaked(ca, prop, "SABOTAGE Shako"):
            caught += 1
    return n, caught


def _attempt_non_dict_mapping(ca, n=6):
    """A Mapping that is not a dict subclass — isinstance(prop, dict) was the whole on-switch."""
    from collections import UserDict
    caught = 0
    for _ in range(n):
        prop = UserDict({"ok": True, "owned": [dict(_DIRTY)], "unsure": [], "throwOut": []})
        if not _leaked(ca, prop, "SABOTAGE Shako"):
            caught += 1
    return n, caught


def _attempt_throwout_evidence(ca, n=6):
    """An ungated lane must not carry a field that can be mistaken for corroboration."""
    caught = 0
    for _ in range(n):
        prop = {"ok": True,
                "owned": [{"name": "decoy", "lane": "stash", "kind": "rune", "count": 1,
                           "evidence": list(_CLEAN_EV)}],
                "unsure": [],
                "throwOut": [dict(_DIRTY)]}
        restore, sent = _stub_board()
        try:
            ca.vault_apply(proposal=prop)
            js = sent.get("js") or ""
            import re as _re
            m = _re.search(r'"throwOut":\s*(\[.*?\])', js)
            t = m.group(1) if m else ""
            # ⚠ THE KEY, NOT THE WORD. The first cut searched for the substring "evidence" and
            # reported 0 of 6 caught — because _DIRTY's own NAME is "SABOTAGE Shako — no evidence,
            # must never be written", so the needle matched my own label. The door was correct
            # the whole time. [[feedback-suspect-the-instrument]] [[source-reading-guard]]
            if t and '"evidence"' not in t and '"witnesses"' not in t:
                caught += 1
        finally:
            restore()
    return n, caught


CLAIMS = (
    ("ungated", "a hand-supplied proposal whose rows clear no witness gate must be refused AT THE "
                "WRITE, not only at the sweep", _attempt_ungated),
    ("empty", "an empty proposal must refuse rather than fall through to whatever was last swept",
     _attempt_empty),
    ("poison-row", "a ROW whose .get('evidence') answers the gate once must not reach the board — "
                   "the stored dict carries no witnesses at all", _attempt_poison_row),
    ("flip-container", "a CONTAINER that answers the gate and the write differently must not land "
                       "the row it hid", _attempt_flip_container),
    ("non-dict-mapping", "a Mapping that is not a dict subclass must not skip the re-gate — "
                         "isinstance(prop, dict) was the entire on-switch", _attempt_non_dict_mapping),
    ("throwout-evidence", "the ungated throw-out lane must not carry an evidence field that can be "
                          "mistaken for corroboration", _attempt_throwout_evidence),
)


def _once(ca, proposal, needle):
    """One caller-supplied body. Refused means ok is false and the needle never reached the board."""
    restore, sent = _stub_board()
    try:
        try:
            r = ca.vault_apply(proposal=proposal)
        except Exception:
            return 1, 0
        js = sent.get("js") or ""
        leaked = bool(needle) and needle in js
        refused = isinstance(r, dict) and r.get("ok") is False and not leaked
        return 1, (1 if refused else 0)
    finally:
        restore()


def _dirty(name):
    return {"name": name, "lane": "stash", "kind": "item", "count": 1, "evidence": []}


def _clean(name):
    return {"name": name, "lane": "stash", "kind": "item", "count": 1,
            "evidence": [{"session": "s1", "witness": "s1#0", "conf": 0.9},
                         {"session": "s2", "witness": "s2#0", "conf": 0.9}]}


def _box(owned=None, unsure=None, throw=None):
    return {"ok": True, "owned": owned or [], "unsure": unsure or [], "throwOut": throw or []}


def _attempt_unsure_only(ca, n=1):
    return _once(ca, _box(unsure=[_dirty("SABOTAGE unsure-only")]), "SABOTAGE unsure-only")


def _attempt_mixed_owned(ca, n=1):
    """A corroborated row must not carry an uncorroborated sibling into the write."""
    return _once(ca, _box(owned=[_clean("decoy clean"), _dirty("SABOTAGE mixed-owned")]),
                 "SABOTAGE mixed-owned")


def _attempt_mixed_unsure(ca, n=1):
    return _once(ca, _box(owned=[_clean("decoy clean")],
                          unsure=[_dirty("SABOTAGE mixed-unsure")]),
                 "SABOTAGE mixed-unsure")


def _attempt_row_string(ca, n=1):
    return _once(ca, _box(owned=["SABOTAGE row-string"]), "SABOTAGE row-string")


def _attempt_row_none(ca, n=1):
    return _once(ca, _box(owned=[None]), "SABOTAGE")


def _attempt_evidence_string(ca, n=1):
    row = _dirty("SABOTAGE evidence-string")
    row["evidence"] = "s1,s2,s3"
    return _once(ca, _box(owned=[row]), "SABOTAGE evidence-string")


def _attempt_evidence_dict(ca, n=1):
    row = _dirty("SABOTAGE evidence-dict")
    row["evidence"] = {"session": "s1", "conf": 0.9}
    return _once(ca, _box(owned=[row]), "SABOTAGE evidence-dict")


def _attempt_evidence_int(ca, n=1):
    row = _dirty("SABOTAGE evidence-int")
    row["evidence"] = 3
    return _once(ca, _box(owned=[row]), "SABOTAGE evidence-int")


def _attempt_witnesses_string(ca, n=1):
    row = {"name": "SABOTAGE witnesses-string", "lane": "stash", "kind": "item", "count": 1,
           "witnesses": "s1 and s2"}
    return _once(ca, _box(owned=[row]), "SABOTAGE witnesses-string")


def _attempt_one_session(ca, n=1):
    row = _dirty("SABOTAGE one-session")
    # Same witness id twice. Two different witness ids are two looks, which the keep bar
    # is allowed to count; one id repeated is one eye, and one eye is not enough.
    row["evidence"] = [{"session": "s1", "witness": "s1", "conf": 0.99},
                       {"session": "s1", "witness": "s1", "conf": 0.99}]
    return _once(ca, _box(owned=[row]), "SABOTAGE one-session")


def _attempt_low_conf(ca, n=1):
    row = _dirty("SABOTAGE low-conf")
    row["evidence"] = [{"session": "s1", "witness": "s1#0", "conf": 0.1},
                       {"session": "s2", "witness": "s2#0", "conf": 0.1}]
    return _once(ca, _box(owned=[row]), "SABOTAGE low-conf")


def _attempt_conf_string(ca, n=1):
    row = _dirty("SABOTAGE conf-string")
    row["evidence"] = [{"session": "s1", "witness": "s1#0", "conf": "0.99"},
                       {"session": "s2", "witness": "s2#0", "conf": "high"}]
    return _once(ca, _box(owned=[row]), "SABOTAGE conf-string")


def _attempt_conf_bool(ca, n=1):
    row = _dirty("SABOTAGE conf-bool")
    row["evidence"] = [{"session": "s1", "witness": "s1#0", "conf": True},
                       {"session": "s2", "witness": "s2#0", "conf": True}]
    return _once(ca, _box(owned=[row]), "SABOTAGE conf-bool")


def _attempt_conf_nan(ca, n=1):
    row = _dirty("SABOTAGE conf-nan")
    row["evidence"] = [{"session": "s1", "witness": "s1#0", "conf": float("nan")},
                       {"session": "s2", "witness": "s2#0", "conf": float("nan")}]
    return _once(ca, _box(owned=[row]), "SABOTAGE conf-nan")


def _attempt_cycle(ca, n=1):
    row = _dirty("SABOTAGE cycle")
    row["self"] = row
    return _once(ca, _box(owned=[row]), "SABOTAGE cycle")


def _attempt_items_liar(ca, n=1):
    class LieMap(dict):
        def items(self):
            return [("ok", True), ("owned", [_dirty("SABOTAGE items-liar")]),
                    ("unsure", []), ("throwOut", [])]
        def get(self, k, default=None):
            if k == "owned":
                return [_clean("decoy the get path")]
            return dict.get(self, k, default)
    return _once(ca, LieMap(), "SABOTAGE items-liar")


def _attempt_items_raise(ca, n=1):
    class Boom(dict):
        def items(self):
            raise RuntimeError("items will not answer")
    return _once(ca, Boom({"owned": [_dirty("SABOTAGE items-raise")]}), "SABOTAGE items-raise")


def _attempt_proposal_list(ca, n=1):
    return _once(ca, [_dirty("SABOTAGE proposal-list")], "SABOTAGE proposal-list")


def _attempt_proposal_string(ca, n=1):
    return _once(ca, '{"owned":[{"name":"SABOTAGE proposal-string","evidence":[]}]}',
                 "SABOTAGE proposal-string")


def _attempt_throw_only(ca, n=1):
    return _once(ca, _box(throw=[_dirty("SABOTAGE throw-only")]), "SABOTAGE throw-only")


def _attempt_owned_string(ca, n=1):
    return _once(ca, {"ok": True, "owned": "SABOTAGE owned-string", "unsure": [], "throwOut": []},
                 "SABOTAGE owned-string")


def _attempt_depth(ca, n=1):
    body = _dirty("SABOTAGE depth")
    for _ in range(12):
        body = {"wrap": body}
    return _once(ca, _box(owned=[body]), "SABOTAGE depth")


def _attempt_evidence_nondicts(ca, n=1):
    row = _dirty("SABOTAGE evidence-nondicts")
    row["evidence"] = ["s1", "s2", "s3"]
    return _once(ca, _box(owned=[row]), "SABOTAGE evidence-nondicts")


def _attempt_int_keys(ca, n=1):
    return _once(ca, {1: [_dirty("SABOTAGE int-keys")], "unsure": [], "throwOut": []},
                 "SABOTAGE int-keys")


def _attempt_wrong_case_lane(ca, n=1):
    return _once(ca, {"ok": True, "Owned": [_dirty("SABOTAGE wrong-case")],
                      "unsure": [], "throwOut": []},
                 "SABOTAGE wrong-case")


CLAIMS = CLAIMS + (
    ("unsure-only", "an uncorroborated row under unsure, with owned empty, must not reach the board",
     _attempt_unsure_only),
    ("mixed-owned", "one corroborated row must not carry an uncorroborated sibling into the write",
     _attempt_mixed_owned),
    ("mixed-unsure", "a dirty unsure row must refuse the proposal even when owned is clean",
     _attempt_mixed_unsure),
    ("row-string", "a row that is a string is not a record and must not be written",
     _attempt_row_string),
    ("row-none", "a None row must not be walked as a record",
     _attempt_row_none),
    ("evidence-string", "evidence that is a sentence is not a list of sightings",
     _attempt_evidence_string),
    ("evidence-dict", "one evidence object is not a list of sightings",
     _attempt_evidence_dict),
    ("evidence-int", "a count standing in for the evidence list is not evidence",
     _attempt_evidence_int),
    ("witnesses-string", "a witnesses string must not satisfy the gate in place of sightings",
     _attempt_witnesses_string),
    ("one-session", "two sightings from the SAME session are one witness, and one is not enough",
     _attempt_one_session),
    ("low-conf", "two sessions below the confidence floor are still unsure",
     _attempt_low_conf),
    ("conf-string", "a confidence written as text is not a confidence",
     _attempt_conf_string),
    ("conf-bool", "True is not a confidence of 1",
     _attempt_conf_bool),
    ("conf-nan", "NaN confidence is arithmetic that already lost its meaning",
     _attempt_conf_nan),
    ("cycle", "a self-referential row must refuse rather than recurse",
     _attempt_cycle),
    ("items-liar", "a mapping whose items() and get() disagree must be judged on items(), the inert copy",
     _attempt_items_liar),
    ("items-raise", "a mapping that will not yield items must not fall through to the last sweep",
     _attempt_items_raise),
    ("proposal-list", "a list is not a proposal record and must not fall through to the last sweep",
     _attempt_proposal_list),
    ("proposal-string", "a JSON string is not a record; the door must not parse it as a second path",
     _attempt_proposal_string),
    ("throw-only", "a proposal that is only throw-outs has nothing to register and must refuse",
     _attempt_throw_only),
    ("owned-string", "owned as a string is not a list of rows",
     _attempt_owned_string),
    ("depth", "a row buried past the inert depth cap must fail closed, not be recovered",
     _attempt_depth),
    ("evidence-nondicts", "a list of strings is not a list of sightings",
     _attempt_evidence_nondicts),
    ("int-keys", "integer keys are not the owned/unsure/throwOut lanes",
     _attempt_int_keys),
    ("wrong-case", "the lane Owned is not the lane owned",
     _attempt_wrong_case_lane),
)


def score():
    try:
        import confidence
        import control_app as ca
    except Exception as e:
        return [{"claim": c, "what": w, "attempts": None, "caught": None, "wilson": None,
                 "state": "UNKNOWN",
                 "notes": ["the console module would not import (%s) — UNKNOWN, not a pass"
                           % str(e)[:70]]} for c, w, _ in CLAIMS]
    rows = []
    for claim, what, fn in CLAIMS:
        notes = []
        try:
            n, k = fn(ca)
        except Exception as e:
            n, k = None, None
            notes.append("the attempt itself raised (%s) — UNKNOWN, the guard is unmeasured"
                         % str(e)[:90])
        if not n:
            state, wil = ("UNPROVEN" if n == 0 else "UNKNOWN"), None
        elif k < n:
            state = "LEAKS"
            wil = confidence.wilson_lower(k, n)
            notes.append("a proposal the vault MUST refuse was accepted %d time(s) of %d — that is "
                         "a write into his ledger on evidence nothing corroborated" % (n - k, n))
        else:
            state, wil = "PROVEN", confidence.wilson_lower(k, n)
        rows.append({"claim": claim, "what": what, "attempts": n, "caught": k, "wilson": wil,
                     "state": state, "notes": notes})
    return rows


def forget_note():
    """-> str. Where vault.forget's evidence comes from, stated rather than left blank."""
    return ("vault.forget is attacked by its own harness, vault_forget_wilson.py (REG-3819): the ledger "
            "drop refuses while any row cites only reels gone from disk. This harness never attacks it.")


def score_live(port=17772, n=8, timeout=6.0):
    """The SAME refusal, asked of the RUNNING console over HTTP. -> row or None

    ⚠ WHY THIS EXISTS AND WHY IT IS A DIFFERENT KIND. `score()` above imports the module and calls
    the function; that is a sabotage, and sabotage is one kind of evidence. vault.apply carries
    kinds_bar 1.3 precisely so that one kind cannot open it — "Wilson counts how many looks agreed,
    never whether they were independent". Asking the LIVE console, over the wire, through the route
    his own UI posts to, is a genuinely different witness: it exercises the routing, the JSON body
    handling and the running process, none of which an import touches.

    ⚠ IT IS STILL THE SAFE ATTEMPT. Every row carries an empty evidence list, so the re-gate
    rejects the proposal before the board is asked. Verified with ONE request before any batch was
    sent: ok False, and the response NAMES the rejected row.

    ⚠ AN UNREACHABLE CONSOLE BANKS NOTHING. Returns None, which the caller reports as UNKNOWN —
    never as a pass. A dead endpoint is an empty seat, not agreement.
    """
    import json as _json
    import urllib.request as _u
    caught, attempted = 0, 0
    body = _json.dumps({"proposal": {"owned": [{"name": "SABOTAGE PROBE — no evidence, must never "
                                                       "be written", "evidence": []}],
                                     "unsure": [], "throwOut": []}}).encode("utf-8")
    for _ in range(n):
        try:
            req = _u.Request("http://127.0.0.1:%d/api/vault_apply" % port, data=body,
                             headers={"Content-Type": "application/json"})
            r = _json.loads(_u.urlopen(req, timeout=timeout).read().decode("utf-8", "replace"))
        except Exception:
            return None                  # unreachable -> UNKNOWN, and nothing is banked
        attempted += 1
        if isinstance(r, dict) and r.get("ok") is False and "gate" in str(r.get("why", "")).lower():
            caught += 1
    if not attempted:
        return None
    import confidence
    return {"claim": "live-ungated", "attempts": attempted, "caught": caught,
            "wilson": confidence.wilson_lower(caught, attempted),
            "state": "PROVEN" if caught == attempted else "LEAKS",
            "what": "the RUNNING console, over its own HTTP route, refuses a proposal whose rows "
                    "clear no witness gate",
            "notes": ([] if caught == attempted else
                      ["the live console ACCEPTED %d of %d proposals it must refuse — that is a "
                       "write into his ledger over the wire" % (attempted - caught, attempted)])}


def bank_into_proof_queue(rows):
    import self_arming as _sa
    banked, skipped = [], []
    for r in rows:
        n, k = r.get("attempts"), r.get("caught")
        if n is None or k is None:
            skipped.append("%s (%s — banks nothing)" % (r.get("claim"), r.get("state")))
            continue
        try:
            _sa.bank("vault.apply", "sabotage", "vault_wilson", n=n, k=k,
                     attacks=1,   # ⚠ ONE ROW = ONE ATTACK FUNCTION; `n` is how many times it was
                     # applied. Summing these across rows gives the DISTINCT attack count,
                     # which is what stops a Wilson score being bought by looping one idea
                     # over many inputs. See self_arming.bank() and REG-598.
                     ref=str(r.get("claim")), note=str(r.get("what") or "")[:200])
            banked.append("%s %d/%d" % (r.get("claim"), k, n))
        except ValueError as e:
            skipped.append("%s REFUSED: %s" % (r.get("claim"), str(e)[:120]))
    return {"banked": banked, "skipped": skipped}


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    rows = score()
    # ⚠⚠ v2940 (#75) — BANKING IS NOW DELIBERATE, BECAUSE AN AUDIT THAT WRITES EVIDENCE IS NOT AN
    # AUDIT. MEASURED 2026-09-11: all four wilson harnesses called bank_into_proof_queue()
    # unconditionally from main(), and all four are REGISTERED GATES (hover_wilson appears 8 times
    # in run_gates.py). So every `git push` wrote rows into his self-arming ledger as a SIDE EFFECT
    # of grading the tree — 333 rows across 18 axes, and roughly twenty of this session's pushes
    # contributed. Evidence must be banked because someone decided to, never because a gate ran.
    # ⚠ The FOLD was never the problem: `_fold` keys on (lock, kind, src, ref) and score() folds
    # before scoring, so repetition never inflated n — measured on console.pixel_rescue,
    # n == attacks == 16 and wilson == wilsonByAttack. Only the door was open.
    b = bank_into_proof_queue(rows) if "--bank" in argv else {"banked": [], "skipped": ["not banked: pass --bank to write evidence. An audit that writes is not an audit."]}
    # the LIVE witness, banked under its own kind so confluence can see two independent sources
    live = score_live()
    live_note = ""
    if live is None:
        live_note = ("the running console could not be reached, so there is no LIVE witness — "
                     "UNKNOWN, not a pass, and nothing was banked for it")
    elif "--bank" not in argv:
        # ⚠⚠ v2940 (#75) — THE SECOND DOOR, and the first fix missed it. Guarding
        # bank_into_proof_queue() alone still left this LIVE-witness bank writing on every plain
        # `python3 tv/vault_wilson.py`. MEASURED: three CLI audits after that fix still moved the
        # ledger 333 -> 334, and the row that landed was exactly `vault.apply / live / vault_live`.
        # Counting the bank CALLS per file (4/2/3/1) and guarding only the shared one is how a
        # sweep misses the sibling — the same shape as REG-942. [[sweep-dont-ask]]
        live_note = ("a LIVE witness was read but NOT banked — pass --bank to write it. "
                     "Reading is not evidence until someone decides it is.")
    else:
        try:
            import self_arming as _sa
            _sa.bank("vault.apply", "live", "vault_live", n=live["attempts"], k=live["caught"],
                     attacks=1,   # ⚠ ONE ROW = ONE ATTACK FUNCTION; `n` is how many times it was
                     # applied. Summing these across rows gives the DISTINCT attack count,
                     # which is what stops a Wilson score being bought by looping one idea
                     # over many inputs. See self_arming.bank() and REG-598.
                     ref=live["claim"], note=live["what"][:200])
            live_note = ("banked LIVE -> vault.apply: %s %d/%d"
                         % (live["claim"], live["caught"], live["attempts"]))
        except ValueError as e:
            live_note = "live NOT banked: %s" % str(e)[:140]
    print("VAULT WILSON — can the write door refuse when it must?\n")
    print("  %-9s %9s %8s %8s  %s" % ("claim", "sabotages", "caught", "wilson", "state"))
    print("  " + "-" * 58)
    for r in rows:
        print("  %-9s %9s %8s %8s  %s" % (
            r["claim"], "?" if r["attempts"] is None else r["attempts"],
            "?" if r["caught"] is None else r["caught"],
            "—" if r["wilson"] is None else ("%.3f" % r["wilson"]), r["state"]))
    print()
    if b["banked"]:
        print("  banked -> vault.apply: " + ", ".join(b["banked"]))
    for sk in b["skipped"]:
        print("  NOT banked: " + sk)
    for r in rows:
        for n in (r["notes"] or []):
            print("  %-9s %s" % (r["claim"], n))
    if live is not None:
        print("  %-9s %9s %8s %8s  %s" % (live["claim"], live["attempts"], live["caught"],
                                          "%.3f" % live["wilson"], live["state"]))
    print("  " + live_note)
    print("\n  vault.forget: " + forget_note())
    print("\n  ⚠ nothing was applied. Every attempt is a proposal the door MUST reject, and each "
          "is rejected before the board is asked.")
    # ⚠⚠ v2888 — WAS `return 0`, UNCONDITIONALLY. heart2 named this one of three gates that could
    # never go red however bad the answer got: it scored every sabotage and then discarded the
    # verdict. Its sibling hover-wilson already exits 1 on a LEAKS row, so this makes a law that
    # exists elsewhere apply here too rather than inventing one. MEASURED BEFORE ARMING, 2026-09-10:
    # 2 claims, 8 of 8 sabotages caught on each, 0 LEAKS — so arming blocks nothing today and catches the
    # first sabotage that ever gets through. An UNPROVEN claim still PASSES, loudly: nobody having
    # tried to break it yet is work to do, not a defect. [[the-unjoined-end]] [[regression-guard]]
    _leaks = [r for r in rows if r.get("state") == "LEAKS"]
    if _leaks:
        print("")
        print("LEAK - a deliberately WRONG input was NOT caught:")
        for _r in _leaks:
            print("   %s (%s): caught %s of %s sabotages"
                  % (_r.get("claim"), _r.get("what"), _r.get("caught"), _r.get("attempts")))
        return 1
    return 0


RED_PROOF = [
    {
        "why": "v2889 — the tamper makes EVERY proposal row clear the witness gate, so a hand-supplied "
               "proposal is written without ever being re-checked at the door. vault-wilson exits 1 "
               "only on a LEAKS row and a probe that RAISES is UNKNOWN (loud, and PASSING), so the "
               "tamper had to make a refusal ACCEPT rather than break. MEASURED against a shadowed "
               "control_app before this was written: ungated LEAKS, sabotages=8 caught=0, exit 1 — "
               "and `empty` stayed PROVEN 8/8, which is what shows the probe still works rather than "
               "being globally broken. [[sabotage-is-usually-the-wrong-one]]",
        "file": 'control_app.py',
        # ⚠⚠ v3127 — RE-ANCHORED, COUNTED NOT GUESSED. `_kept` became `_kept[_which]` when the
        # approved rows were split into owned/unsure, and this proof was never swept with it — so
        # its `find` matched 0 times and the gate carried a verdict about a line that no longer
        # exists. That is the sabotage's fault, not the law's. [[sweep-dont-ask]] [[copy-drift]]
        "find": '(_kept[_which] if _v.get("pass") else _dropped).append(_r)',
        "replace": '(_kept[_which]).append(_r)',
        "matches": 1,
    },
]

if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    raise SystemExit(main())
