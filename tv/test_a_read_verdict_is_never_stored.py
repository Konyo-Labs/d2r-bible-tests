# -*- coding: utf-8 -*-
"""#79 — A VERDICT THE READ PATH INVENTS ABOUT ITSELF MUST NEVER BECOME STORED STATE.

MEASURED ON HIS LIVE `tv/shadow_watch.json`, 2026-09-12:

    {"_prov": {"by":"control_app","at":1789166507975,"store":"shadow_watch"},
     "ok": false, "why": "the shadow reader is switched off", "lookedAt": 1789166507974}

`ok` is there and NO CALLER CAN PASS IT. All six call sites of `_shadow_watch_note` are inside
`shadow_watch_tick` (control_app.py 21318/21337/21342/21347/21350/21364) and their keyword sets —
AST-parsed, not grepped — are lookedAt / sawAt / startedAt / starts / unknown / why. Never `ok`.
Nor did any commit ever pass it: `git log -S'_shadow_watch_note(ok'` is empty.

WHERE IT CAME FROM. `_shadow_watch_note` seeded itself with `cur = shadow_watch_state()`, and that
function exists to answer a READER, so each of its failure paths returns a DIAGNOSTIC dict wearing
`ok`: `{"ok": False, "why": "the record is unreadable: ..."}`, `{"ok": False, "why": "the record is
not a mapping"}`, `{"ok": True, ..., "why": "the watcher has never written a record"}`. One
unreadable moment therefore became the seed of the next write; `cur.update(kw)` laid the tick's
real fields on top, and the lockless read-modify-write carried the sentinel forward every 20 s
thereafter, because nothing ever removes a key. The record above is the result — a CHIMERA, a true
current `why` from a real tick beside a false stale `ok` from a different event.

WHAT IT COST, measured by running both consumers against both shapes:

    health_engine.check_shadow_watch   POISONED -> unknown        HEALED -> ok
    corroborate shadow-armed-is-watching   right() -> None (UNGRADED)  ->  gradeable

Both test `w.get("ok") is False` FIRST and give up, so one laundered key held a health row at
UNKNOWN and left a corroborator invariant ungraded — the invariant guarding "an evening of play
produced no reels while the panel read 'armed'". check_shadow_watch's own docstring cites
[[label-outlived-referent]]; it was an instance of the scar it was written to catch.

THIS LAW PINS THREE THINGS, each of which was separately wrong:
  1. the writer seeds from the PERSISTED record, never from the reader's diagnostic;
  2. `ok` is dropped on the way out, which also HEALS the poisoned record on the next tick;
  3. the write is ATOMIC — a plain open(...,"w") truncates before json.dump runs, and the
     unreadable file that leaves behind is exactly what mints the sentinel in the first place.
     The defect was circular: the torn write CAUSED the bad read that poisoned the store.

⚠ THE BEHAVIOURAL TEST IS THE REAL ONE. The three source checks below can only see the shapes I
thought of; only the round trip proves a poisoned record actually heals.
[[unknown-stays-unknown]] [[open-for-write-truncates-first]] [[label-outlived-referent]]
"""
import ast
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

SRC = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()


def _fn(name):
    """The AST node of a module-level def, so a law about CODE reads code and not prose."""
    for node in ast.parse(SRC).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


class AReadVerdictIsNeverStored(unittest.TestCase):

    # ── 1. the seed ───────────────────────────────────────────────────────────────────────────
    def test_the_writer_does_not_seed_itself_from_the_reader(self):
        fn = _fn("_shadow_watch_note")
        self.assertIsNotNone(fn, "_shadow_watch_note is gone — this law has no subject")
        called = {n.func.id for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertNotIn(
            "shadow_watch_state", called,
            "_shadow_watch_note seeds `cur` from shadow_watch_state(), whose failure paths return "
            "diagnostic dicts carrying `ok` — that is how a read verdict became stored state. "
            "Seed from the persisted record (_shadow_watch_stored) instead.")

    # ── 2. the sentinel is dropped ────────────────────────────────────────────────────────────
    def test_the_sentinel_key_is_dropped_before_the_write(self):
        fn = _fn("_shadow_watch_note")
        pops = [n for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "pop" and n.args
                and isinstance(n.args[0], ast.Constant) and n.args[0].value == "ok"]
        self.assertTrue(pops,
                        "nothing removes `ok` on the way out, so a record already poisoned stays "
                        "poisoned for every future tick — the store has no other way to lose a key")

    # ── 3. the write is atomic ────────────────────────────────────────────────────────────────
    def test_the_write_is_atomic(self):
        fn = _fn("_shadow_watch_note")
        repl = [n for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "replace"]
        self.assertTrue(repl,
                        "the note is written with a bare open(...,'w'), which TRUNCATES before "
                        "json.dump runs; the unreadable file that leaves behind is what mints the "
                        "`ok` sentinel this whole law exists to keep out of the store")

    # ── 4. THE ROUND TRIP — a poisoned record must heal ────────────────────────────────────────
    def test_a_poisoned_record_heals_on_the_next_tick(self):
        d = tempfile.mkdtemp(prefix="shadow_law_")
        self.addCleanup(shutil.rmtree, d, True)
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = d
        self.addCleanup(lambda: os.environ.__setitem__("TV_HIST", old) if old is not None
                        else os.environ.pop("TV_HIST", None))
        import control_app as CA
        p = CA._shadow_watch_path()
        self.assertIn(os.path.normcase(os.path.realpath(d)), os.path.normcase(os.path.realpath(p)),   # #107 - 8.3 names
                      "TV_HIST was not honoured — REFUSING to run against a real store")

        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"ok": False, "why": "the shadow reader is switched off", "lookedAt": 1789166507974}))
        CA._shadow_watch_note(lookedAt=1789166999999, why="the shadow reader is switched off")
        got = json.load(io.open(p, encoding="utf-8"))

        self.assertNotIn("ok", got,
                         "the laundered sentinel survived a write — it will survive every write")
        self.assertEqual(got.get("lookedAt"), 1789166999999,
                         "the tick's real field did not land, so this healed by losing data")
        self.assertEqual(got.get("why"), "the shadow reader is switched off",
                         "the caller's `why` was lost")

    # ── 5. and the health row must actually move ──────────────────────────────────────────────
    def test_the_health_row_is_no_longer_held_at_unknown(self):
        d = tempfile.mkdtemp(prefix="shadow_law_h_")
        self.addCleanup(shutil.rmtree, d, True)
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = d
        self.addCleanup(lambda: os.environ.__setitem__("TV_HIST", old) if old is not None
                        else os.environ.pop("TV_HIST", None))
        import control_app as CA
        import health_engine as HE
        p = CA._shadow_watch_path()
        self.assertIn(os.path.normcase(os.path.realpath(d)), os.path.normcase(os.path.realpath(p)),   # #107 - 8.3 names
                      "TV_HIST was not honoured — REFUSING to run against a real store")

        def state(rec):
            io.open(p, "w", encoding="utf-8").write(json.dumps(rec))
            return (HE.check_shadow_watch() or {}).get("state")

        poisoned = state({"ok": False, "why": "the shadow reader is switched off",
                          "lookedAt": 1789166507974})
        healed = state({"why": "the shadow reader is switched off",
                        "lookedAt": int(__import__("time").time() * 1000)})  # FRESH, not a frozen instant: the OK path requires a look within 10 min, so a hardcoded timestamp rots the law 10 minutes after it is written
        self.assertEqual(poisoned, "unknown",
                         "the poisoned shape no longer reaches UNKNOWN, so this test has stopped "
                         "measuring the defect it was written for — re-derive it, do not delete it")
        self.assertEqual(healed, "ok",
                         "with the sentinel gone the row STILL does not reach a verdict, so the "
                         "short-circuit was not the only thing holding it at UNKNOWN")


RED_PROOF = [
    {
        "why": "putting the reader's diagnostic back as the seed is the original defect; the AST "
               "law must turn red",
        "file": "control_app.py",
        "find": "    cur = _shadow_watch_stored()\n    if cur is None:",
        "replace": "    cur = shadow_watch_state()\n    if cur is None:",
        "matches": 1,
    },
    {
        "why": "removing the pop leaves a poisoned record poisoned forever — both the AST law and "
               "the round trip must turn red",
        "file": "control_app.py",
        "find": '    cur.pop("ok", None)',
        "replace": "    pass",
        "matches": 1,
    },
    {
        "why": "going back to the truncating write restores the torn file that mints the sentinel",
        "file": "control_app.py",
        "find": "        os.replace(_tmp, _p)",
        "replace": "        pass",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
