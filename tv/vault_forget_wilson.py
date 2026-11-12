"""REG-3819 (his 11-13 "okay then do it") - can the VAULT FORGET refuse to drop a ledger it could not rebuild?

`vault.forget` guards "drops the ledger". Until REG-3819 the door had no refusal path (one return, always ok) and
its lock was declared UNPROVABLE: there was no state in which it had to say no. Its docstring called the drop safe
"because the ledger is rebuildable from the reels" - and measured on his Mac on 11-13, 24 of the 184 ledger rows
already cited only reels the river had released. For those rows the ledger was the only record left.

So the drop now refuses while any row's every witness reel is gone, and while the ledger or the reel store will not
read. That refusal is what this harness attacks.

⚠⚠ THIS HARNESS NEVER TOUCHES HIS LEDGER. Every attempt runs in a scratch directory under the system temp dir: the
ledger path, the swept-memory path and the reel store are all pointed there before the first call, and the harness
REFUSES to run (UNKNOWN, nothing banked) if any of the three still resolves inside the repo. The two stores are put
back by value afterwards. [[feedback-fixtures-never-touch-live-data]]

⚠ A REFUSAL IS COUNTED ONLY IF THE LEDGER BYTES ARE UNCHANGED. A door that answers "refused" and wrote anyway has
not refused, so every attempt compares the file before and after.

⚠ AND THE CONTROL MUST CLEAR. A door that refuses EVERYTHING would score perfectly on the attacks and be a cage, so
the harness first drops a ledger whose every row has its reel on disk and requires that drop to happen. If the
control does not clear, the run is UNKNOWN and nothing is banked: an instrument that always refuses proves nothing.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)

SESSION = "s_1790000000000_00001"
FRAME = "f_1790000000001.jpg"


def _row(name, sessions):
    return {"name": name, "kind": "charm", "lane": "owned", "conf": 0.9, "count": 1, "lastSeenTs": 1790000000,
            "witnesses": [{"session": s, "frame": FRAME} for s in sessions]}


def _ledger(*rows, by_key=None):
    return {"owned": list(rows), "added": [], "raised": [], "held": [], "byKey": by_key or {}}


class _Box(object):
    """A scratch world: a ledger file, a swept file and a reel store, all under the system temp dir."""

    def __init__(self, ca):
        self.ca = ca
        self.root = tempfile.mkdtemp(prefix="vault_forget_wilson_")
        self.hist = os.path.join(self.root, "hist")
        os.makedirs(os.path.join(self.hist, "reel_" + SESSION))
        with open(os.path.join(self.hist, "reel_" + SESSION, FRAME), "wb") as fh:
            fh.write(b"\xff\xd8 a frame")
        self.ledger = os.path.join(self.root, "vault_accum.json")
        self.swept = os.path.join(self.root, "vault_swept.json")
        self._real = (ca.VAULT_LEDGER_PATH, ca._VAULT_SWEPT_PATH, ca.HIST_DIR)

    def __enter__(self):
        ca = self.ca
        for p in (self.ledger, self.swept, self.hist):
            if os.path.abspath(p).startswith(os.path.abspath(REPO) + os.sep):
                raise RuntimeError("a scratch path resolved inside the repo - refusing to run near his ledger")
        ca.VAULT_LEDGER_PATH, ca._VAULT_SWEPT_PATH, ca.HIST_DIR = self.ledger, self.swept, self.hist
        return self

    def __exit__(self, *exc):
        ca = self.ca
        ca.VAULT_LEDGER_PATH, ca._VAULT_SWEPT_PATH, ca.HIST_DIR = self._real
        for p in (self.ledger, self.swept):
            ca._UNREADABLE.discard(p)
        shutil.rmtree(self.root, ignore_errors=True)
        return False

    def write(self, obj=None, raw=None):
        with open(self.ledger, "w", encoding="utf-8") as fh:
            fh.write(raw if raw is not None else json.dumps(obj))

    def ledger_bytes(self):
        try:
            with open(self.ledger, "rb") as fh:
                return fh.read()
        except OSError:
            return None


def _refused(box, ledger_obj=None, raw=None, hist=None):
    """One attempt: True when the drop was refused AND the ledger bytes did not move."""
    box.write(ledger_obj, raw)
    if hist is not None:
        box.ca.HIST_DIR = hist
    before = box.ledger_bytes()
    r = box.ca.vault_forget(ledger=True)
    after = box.ledger_bytes()
    box.ca.HIST_DIR = box.hist
    return (isinstance(r, dict) and r.get("refused") is True and r.get("ledgerCleared") is False
            and before == after)


def _attempt_reel_gone(box):
    """a row whose only witness reel was released"""
    return _refused(box, _ledger(_row("gone", ["s_1790000000000_99999"])))


def _attempt_no_session(box):
    """a row whose witnesses name no session at all"""
    led = _ledger({"name": "nameless", "witnesses": [{"frame": FRAME}, {"frame": FRAME}]})
    return _refused(box, led)


def _attempt_empty_witnesses(box):
    """a row with an empty witness list - nothing to rebuild it from"""
    return _refused(box, _ledger({"name": "bare", "witnesses": []}))


def _attempt_traversal(box):
    """a session spelled to walk out of the reel store: reel_s_x/../.. is the store's parent, which exists.

    reel_s_x is made first: a POSIX kernel resolves each component, so without it the climb dies on a missing folder
    and the attempt could not tell a door with the name check from one without it (Windows folds .. by text first)."""
    os.makedirs(os.path.join(box.hist, "reel_s_x"), exist_ok=True)
    return _refused(box, _ledger(_row("climb", ["s_x/../.."])))


def _attempt_not_a_reel_name(box):
    """a session without the s_ prefix whose reel_<name> directory DOES exist - not a reel name, not a witness"""
    os.makedirs(os.path.join(box.hist, "reel_scratch"), exist_ok=True)
    return _refused(box, _ledger(_row("impostor", ["scratch"])))


def _attempt_witness_not_a_dict(box):
    """witnesses that are bare strings naming a reel that is on disk"""
    return _refused(box, _ledger({"name": "strings", "witnesses": [SESSION, SESSION]}))


def _attempt_frame_released(box):
    """the reel folder is still there but the witness frame was released from it - the folder is not the evidence"""
    return _refused(box, _ledger({"name": "released", "witnesses": [{"session": SESSION, "frame": "f_1790000000999.jpg"}]}))


def _attempt_frame_climbs(box):
    """a frame name spelled to reach a file outside the reel folder that does exist"""
    with open(os.path.join(box.hist, "outside.jpg"), "wb") as fh:
        fh.write(b"x")
    return _refused(box, _ledger({"name": "climbing frame", "witnesses": [{"session": SESSION, "frame": "../outside.jpg"}]}))


def _attempt_witnesses_not_a_list(box):
    """a row whose witnesses field is a dict naming a frame that IS on disk - it cannot be read as a witness list"""
    return _refused(box, _ledger({"name": "dict witnesses", "witnesses": {"session": SESSION, "frame": FRAME}}))


def _attempt_hidden_in_by_key(box):
    """a gone row nested under byKey, beside a lane whose rows are all fine"""
    led = _ledger(_row("fine", [SESSION]), by_key={"charm": {"deep": [_row("buried", ["s_1790000000000_88888"])]}})
    return _refused(box, led)


def _attempt_mixed_one_gone(box):
    """one rebuildable row and one that is not: one gone row is enough to keep the whole ledger"""
    return _refused(box, _ledger(_row("fine", [SESSION]), _row("gone", ["s_1790000000000_77777"])))


def _attempt_ledger_wrong_shape(box):
    """the ledger file parses but holds a list - UNKNOWN, never an empty ledger"""
    return _refused(box, raw=json.dumps([_row("x", [SESSION])]))


def _attempt_ledger_corrupt(box):
    """the ledger file will not parse - UNKNOWN, never an empty ledger"""
    return _refused(box, raw='{"owned": [ {"name": "half a write"')


def _attempt_store_missing(box):
    """the reel store is not there to ask - UNKNOWN, never 'every reel is gone, so nothing to protect'"""
    return _refused(box, _ledger(_row("fine", [SESSION])), hist=os.path.join(box.root, "no_such_store"))


CLAIMS = (
    ("reel-gone", "a row whose only witness reel was released keeps the ledger", _attempt_reel_gone),
    ("no-session", "a row whose witnesses name no session keeps the ledger", _attempt_no_session),
    ("empty-witnesses", "a row with an empty witness list keeps the ledger", _attempt_empty_witnesses),
    ("traversal", "a session spelled to climb out of the reel store is no witness", _attempt_traversal),
    ("not-a-reel", "a session without the s_ prefix is no witness even if its folder exists", _attempt_not_a_reel_name),
    ("string-witness", "a witness that is a bare string is no witness", _attempt_witness_not_a_dict),
    ("frame-released", "a witness frame released from a reel that is still on disk keeps the ledger", _attempt_frame_released),
    ("frame-climbs", "a frame name spelled to reach outside its reel is no witness", _attempt_frame_climbs),
    ("witnesses-dict", "a witnesses field that is not a list keeps the ledger", _attempt_witnesses_not_a_list),
    ("by-key", "a gone row nested under byKey keeps the ledger", _attempt_hidden_in_by_key),
    ("mixed", "one gone row beside a fine one keeps the whole ledger", _attempt_mixed_one_gone),
    ("wrong-shape", "a ledger that parses as a list is UNKNOWN and kept", _attempt_ledger_wrong_shape),
    ("corrupt", "a ledger that will not parse is UNKNOWN and kept", _attempt_ledger_corrupt),
    ("store-missing", "a reel store that is not there is UNKNOWN and keeps the ledger", _attempt_store_missing),
)


def control(box):
    """-> (ok, why). The door must still CLEAR a ledger whose every row has its reel on disk, and ledger=False must
    clear the swept memory without touching the ledger."""
    box.write(_ledger(_row("fine", [SESSION]), _row("also fine", [SESSION, "s_1790000000000_99999"])))
    before = box.ledger_bytes()
    r0 = box.ca.vault_forget(ledger=False)
    if box.ledger_bytes() != before or not (isinstance(r0, dict) and r0.get("forgot") is True):
        return False, "forgetting the swept memory touched the ledger or did not report forgot (%r)" % (r0,)
    r = box.ca.vault_forget(ledger=True)
    try:
        cleared = json.loads(box.ledger_bytes().decode("utf-8")) == {}
    except Exception:
        cleared = False
    if not (isinstance(r, dict) and r.get("ledgerCleared") is True and cleared):
        return False, "a ledger whose every row has a reel on disk was NOT dropped (%r) - the door is a cage" % (r,)
    return True, ""


def score():
    """-> (rows, control_why). rows: one per claim. control_why is "" when the control cleared."""
    try:
        import confidence
        import control_app as ca
    except Exception as e:
        return ([{"claim": c, "what": w, "attempts": None, "caught": None, "wilson": None, "state": "UNKNOWN",
                  "notes": ["the console module would not import (%s) - UNKNOWN, not a pass" % str(e)[:70]]}
                 for c, w, _ in CLAIMS], "the console module would not import")
    try:
        with _Box(ca) as box:
            ok, why = control(box)
    except Exception as e:
        ok, why = False, "the control itself raised (%s)" % str(e)[:90]
    if not ok:
        return ([{"claim": c, "what": w, "attempts": None, "caught": None, "wilson": None, "state": "UNKNOWN",
                  "notes": ["the control did not clear (%s) - a door that refuses everything proves nothing, so "
                            "nothing is scored" % why]} for c, w, _ in CLAIMS], why)
    rows = []
    for claim, what, fn in CLAIMS:
        notes = []
        try:
            with _Box(ca) as box:
                caught = 1 if fn(box) else 0
            n = 1
        except Exception as e:
            n, caught = None, None
            notes.append("the attempt itself raised (%s) - UNKNOWN, the guard is unmeasured" % str(e)[:90])
        if not n:
            state, wil = "UNKNOWN", None
        elif caught < n:
            state, wil = "LEAKS", confidence.wilson_lower(caught, n)
            notes.append("a ledger the door MUST keep was dropped or reported cleared - that is evidence lost for good")
        else:
            state, wil = "PROVEN", confidence.wilson_lower(caught, n)
        rows.append({"claim": claim, "what": what, "attempts": n, "caught": caught, "wilson": wil,
                     "state": state, "notes": notes})
    return rows, ""


def bank_into_proof_queue(rows):
    import self_arming as _sa
    banked, skipped = [], []
    for r in rows:
        n, k = r.get("attempts"), r.get("caught")
        if n is None or k is None:
            skipped.append("%s (%s - banks nothing)" % (r.get("claim"), r.get("state")))
            continue
        try:
            _sa.bank("vault.forget", "sabotage", "vault_forget_wilson", n=n, k=k,
                     attacks=1,   # ONE ROW = ONE ATTACK FUNCTION (REG-598): looping one idea buys nothing
                     ref=str(r.get("claim")), note=str(r.get("what") or "")[:200])
            banked.append("%s %d/%d" % (r.get("claim"), k, n))
        except ValueError as e:
            skipped.append("%s REFUSED: %s" % (r.get("claim"), str(e)[:120]))
    return {"banked": banked, "skipped": skipped}


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    rows, control_why = score()
    # banking is deliberate (v2940 #75): an audit that writes evidence is not an audit
    b = (bank_into_proof_queue(rows) if "--bank" in argv else
         {"banked": [], "skipped": ["not banked: pass --bank to write evidence. An audit that writes is not an audit."]})
    print("VAULT FORGET WILSON - does the ledger drop refuse when the evidence cannot be rebuilt?\n")
    print("  control: " + ("CLEARED - a rebuildable ledger is still dropped, and the swept memory still clears"
                           if not control_why else "DID NOT CLEAR - " + control_why))
    print("  %-16s %8s %7s %8s  %s" % ("claim", "attempts", "caught", "wilson", "state"))
    print("  " + "-" * 56)
    for r in rows:
        print("  %-16s %8s %7s %8s  %s" % (
            r["claim"], "?" if r["attempts"] is None else r["attempts"], "?" if r["caught"] is None else r["caught"],
            "-" if r["wilson"] is None else ("%.3f" % r["wilson"]), r["state"]))
    for r in rows:
        for n in r["notes"] or []:
            print("  %-16s %s" % (r["claim"], n))
    if b["banked"]:
        print("\n  banked -> vault.forget: " + ", ".join(b["banked"]))
    for sk in b["skipped"]:
        print("  NOT banked: " + sk)
    print("\n  nothing of his was touched: every attempt ran on a scratch ledger under the system temp dir.")
    leaks = [r for r in rows if r.get("state") == "LEAKS"]
    if leaks:
        print("\nLEAK - a ledger the door must keep was dropped:")
        for r in leaks:
            print("   %s (%s)" % (r["claim"], r["what"]))
        return 1
    if control_why:
        print("\nUNKNOWN - the control did not clear, so the attacks prove nothing")
        return 1
    return 0


RED_PROOF = [
    {
        "why": "REG-3819 - the tamper drops the rebuild check, so a row whose every witness reel or frame was released "
               "reads as rebuildable and the ledger is dropped with its evidence. reel-gone, no-session, traversal, "
               "frame-released and by-key must LEAK and the run must exit 1.",
        "file": "control_app.py",
        "find": '                if not (isinstance(w, list) and any(on_disk(x) for x in w)):\n'
                '                    gone.append(o.get("name") or o.get("key") or "a row")',
        "replace": '                if False:\n'
                   '                    gone.append(o.get("name") or o.get("key") or "a row")',
        "matches": 1,
    },
    {
        "why": "REG-3819 - the tamper lets a witness count on its reel FOLDER even when it names a frame, so a frame the "
               "river released from a reel it keeps reads as evidence still on disk: frame-released must LEAK.",
        "file": "control_app.py",
        "find": "        if frame is None:\n            return os.path.isdir(reel)",
        "replace": "        if True:\n            return os.path.isdir(reel)",
        "matches": 1,
    },
    {
        "why": "REG-3819 - the tamper ignores an unreadable ledger, so a corrupt or wrong-shape file reads as an empty "
               "ledger with nothing to protect and the drop goes ahead. The save still refuses on its own, so the door "
               "must SAY refused - and with this tamper it says cleared-or-not without refusing: wrong-shape and "
               "corrupt LEAK.",
        "file": "control_app.py",
        "find": "    gone = None if VAULT_LEDGER_PATH in _UNREADABLE else _ledger_rows_past_their_reels(led)",
        "replace": "    gone = _ledger_rows_past_their_reels(led)",
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
