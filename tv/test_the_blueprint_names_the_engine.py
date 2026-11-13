# -*- coding: utf-8 -*-
"""BLUEPRINT.md MUST NAME EVERY MODULE, AND A CONCEPT MUST FIND ITS OWNER IN ONE GREP.

Konyo, 2026-09-13, after I asked him something the tree already answered: *"so why are you not
checkig blueprints before hand :)?"* and then *"make sure the blueprint is updated accordignly so
you dont need to ask these questions in the future and the blueprints speaks for itself."*

This is `test_the_blueprint_cannot_go_stale`'s sibling one rung down. That one keeps the GATES
section honest; this one keeps the CODE section honest — and the code section did not exist until
v3091, while the tree held **178 modules and 1,045 public functions** and this document said what
none of them were.

⚠⚠ MEASURED THE DAY IT WAS BUILT, and this is the whole justification: `footprint` — a function
shipped hours earlier in slot_identity.py that REFUSES an item overhanging the grid rather than
clipping it — scored **ZERO hits** anywhere in BLUEPRINT.md. So did `occupancy`, `names_loc`,
`terror zone`, `lattice` and `slot identity`. Every one was a shipped, tested behaviour that the
map could not find. A count is not knowledge, and 178 filenames with no purposes is the same
failure `gate_index` was written for one rung up. [[verify-before-building-console]]

⚠ THE SPLIT THIS PINS. Derived every render: which modules exist on disk, and which are imported by
another module — those cannot go stale because nothing stores them. Curated in
`tv/engine_index.json`: purpose, territory, gotcha, entry points, because a sentence about what a
module MEANS cannot be re-derived from an AST. The DRIFT between the two is what this law guards:
a module on disk with no entry (UNINDEXED) or an entry whose file is gone (STALE) must be reported,
never quietly dropped. A map that silently omits a module is worse than no map.

⚠ AND `noPyImporter` SAYS ONLY WHAT IT MEASURES. Two scans of mine disagreed 12-vs-15 on a
"deadEnd" flag, and the cause was one of them counting a module's name inside a `why=` PROSE STRING
in run_gates.py as a real reference. A CLI tool, a hook and a routine are all reached without an
import, so "no module imports it" is a question, never a verdict. [[label-outlived-referent]]
"""
import io
import os
import unittest

from console_safe import enable as _console_safe_enable

_console_safe_enable()

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# the concepts a reader would actually reach for, each a shipped behaviour of this tree
CONCEPTS = ["footprint", "lattice", "occupancy", "slot identity", "names_loc", "sockets",
            "terror zone", "deleter", "second eye", "river", "retention", "tombstone",
            "tooltip", "witness", "wilson", "printer", "vault", "chronicle"]


def _blueprint():
    with io.open(os.path.join(REPO, "BLUEPRINT.md"), encoding="utf-8") as fh:
        return fh.read()


class TestTheBlueprintNamesTheEngine(unittest.TestCase):

    def test_every_module_on_disk_is_named(self):
        import blueprint as B
        rows, drift = B.engine_index()
        self.assertIsNotNone(rows, "tv/engine_index.json could not be read at all")
        print("engine index: %d module(s) · %d unindexed · %d stale"
              % (len(rows), len(drift["unindexed"]), len(drift["stale"])))
        # ⚠⚠ ASSERTING "unindexed IS EMPTY" WENT BLIND, and the drill caught it: a sabotage that
        # hardcodes `"unindexed": []` silences the whole drift report and the assertion passes
        # MORE easily. A law must check the answer is COMPUTED, not that it is convenient. So the
        # difference is re-derived here, independently, and the two must agree.
        # [[sabotage-is-usually-the-wrong-one]]
        self.assertEqual(drift["unindexed"], [],
                         "module(s) on disk with no entry, so the map does NOT describe them: %s"
                         % drift["unindexed"])
        # ⚠⚠ AND PROVE THE REPORT IS COMPUTED, NOT MERELY EMPTY. Two earlier drafts went BLIND in
        # the red-proof drill for the same reason: a sabotage that hardcodes `"unindexed": []`
        # SILENCES the whole drift report, and an assertion that the list is empty then passes MORE
        # easily than before. Re-deriving the set difference in the test did not help either —
        # with a fully indexed tree both sides are empty, so the comparison cannot tell a working
        # report from a disabled one.
        #
        # The only thing that can: put a module on disk that the index does not know about, and
        # require it to be NAMED. Cleaned up in `finally`, so a failure here cannot leave a stray
        # module in his tree. [[sabotage-is-usually-the-wrong-one]] [[feedback-blind-fixture-green-gate]]
        canary = os.path.join(HERE, "zz_drift_canary_delete_me.py")
        try:
            with io.open(canary, "w", encoding="utf-8") as fh:
                fh.write("# temporary: proves engine_index() actually reports drift\n")
            _rows2, drift2 = B.engine_index()
            self.assertIn("zz_drift_canary_delete_me.py", drift2["unindexed"],
                          "a module was added to the tree and the drift report did not name it — "
                          "the report is not derived from the tree, so an UNINDEXED module would "
                          "be dropped from the map in silence, which is the whole failure this "
                          "law exists to prevent")
            print("drift proven live: an unknown module on disk is reported UNINDEXED")
        finally:
            try:
                os.remove(canary)
            except OSError:
                pass
        self.assertFalse(os.path.exists(canary), "the canary module was left in his tree")
        self.assertEqual(drift["stale"], [],
                         "entr(ies) whose file is gone — the map describes code that is not here: %s"
                         % drift["stale"])
        on_disk = [f for f in os.listdir(HERE)
                   if f.endswith(".py") and not f.startswith("test_")]
        self.assertEqual(len(rows), len(on_disk),
                         "%d rows for %d modules on disk" % (len(rows), len(on_disk)))

    def test_a_concept_finds_its_owner_in_one_grep(self):
        """The whole job. Each of these was a shipped behaviour the map could not find.

        ⚠ Grades what render() PRODUCES, not the committed BLUEPRINT.md. Reading the file went
        BLIND: a sabotage that stops emitting the section leaves the checked-in document intact,
        so the law passed while the generator had been gutted. The file is checked too, because a
        reader greps the file — but the generator is the thing under test.
        """
        import blueprint as B
        doc = (B.render() + "\n" + _blueprint()).lower()
        missing = [c for c in CONCEPTS if c not in doc]
        for c in CONCEPTS[:6]:
            print("   %-16s %d hit(s)" % (c, doc.count(c)))
        self.assertEqual(missing, [],
                         "BLUEPRINT.md cannot answer %s — a reader greps the concept, finds "
                         "nothing, and concludes it does not exist. That is the mistake this "
                         "section was built to stop." % missing)

    def test_the_engine_section_is_actually_rendered(self):
        import blueprint as B
        doc = B.render()          # the GENERATOR, not the possibly-stale committed file
        self.assertIn("## THE ENGINE", doc,
                      "render() no longer emits the engine section — BLUEPRINT.md would go back "
                      "to naming zero of the 178 modules on the next regeneration")
        self.assertIn("## THE ENGINE", _blueprint(),
                      "the committed BLUEPRINT.md has no engine section — regenerate it")
        rows, _ = B.engine_index()
        absent = [r["module"] for r in rows if ("**%s**" % r["module"]) not in doc]
        self.assertEqual(absent, [],
                         "%d module(s) are in the index but not rendered into the document: %s"
                         % (len(absent), absent[:6]))
        print("all %d modules rendered as entries" % len(rows))

    def test_a_purpose_may_not_be_a_shrug(self):
        import blueprint as B
        rows, _ = B.engine_index()
        vague = [r["module"] for r in rows
                 if len((r["purpose"] or "").split()) < 5
                 or (r["purpose"] or "").strip().lower() in ("helpers", "utilities", "misc")]
        self.assertEqual(vague, [],
                         "purpose(s) that say nothing: %s. A filename restated is not a purpose, "
                         "and 'helpers' is how a module becomes invisible to the next reader."
                         % vague)
        noaim = [r["module"] for r in rows if not r["purpose"]]
        self.assertEqual(noaim, [], "module(s) with an empty purpose: %s" % noaim)
        print("%d purposes, none empty, none under 5 words" % len(rows))

    def test_every_named_entry_point_still_exists(self):
        """A LABEL THAT OUTLIVED ITS REFERENT (second eye on v3528's 0ab1034b): console_settle.wait was renamed
        wait_until_settled and the index went on naming `wait` - a door no reader can walk through. Measured over the
        whole index that day: 850 named entry points, 4 naming nothing (that one, loose_wires_audit's `main` - it is a
        script with no main - and two run_gates entries whose typed line numbers had drifted 1500 lines). A named entry
        must be a def, class or assignment in its module (run_gates may name a registered gate), and no entry types a
        line number: a number beside a name is the next thing to go stale. CLI lines and route prose are not names and
        are not judged. [[label-outlived-referent]] [[source-reading-guard]]"""
        import ast
        import json
        import re
        with io.open(os.path.join(HERE, "engine_index.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
        gate_names = set()
        with io.open(os.path.join(HERE, "run_gates.py"), encoding="utf-8") as fh:
            for n in ast.walk(ast.parse(fh.read())):
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "Gate" and n.args:
                    gate_names.add(getattr(n.args[0], "value", None))
        stale, typed, named = [], [], 0
        for mod, row in sorted(idx.items()):
            eps = (row or {}).get("entryPoints") if isinstance(row, dict) else None
            if not mod.endswith(".py") or not isinstance(eps, list):
                continue
            with io.open(os.path.join(HERE, mod), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            names |= {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
            for e in eps:
                s = str(e).strip()
                # REG-1637 - the #231 eye on v3531: `\s:\d+\s*$` saw only a bare number at the end, so a range (:362-395),
                # a number with a tail (:1094 (--apply --yes)) and a `->` line kept typing positions. Any position, anywhere.
                if re.search(r"\s:\d+(?:-\d+)?(?![\d.])", s):
                    typed.append("%s: %s" % (mod, s))
                if re.match(r"^(python3?|tvd|--|-|GET|POST|/)", s) or "\u2190" in s or "->" in s:
                    continue
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", s)
                if not m:
                    continue
                named += 1
                if m.group(1) not in names and not (mod == "run_gates.py" and m.group(1) in gate_names):
                    stale.append("%s: %s" % (mod, s))
        self.assertGreater(named, 500, "only %d named entry points were judged - the census read a fragment" % named)
        self.assertEqual(stale, [], "the engine index names doors its modules no longer have:\n  " + "\n  ".join(stale))
        self.assertEqual(typed, [], "an entry point types a line number, which drifts the day the file grows:\n  "
                                    + "\n  ".join(typed))

    def test_the_document_is_deterministic(self):
        """Two renders must differ only in their generated-at line, or the pre-push staleness
        check refuses a tree nobody changed."""
        import blueprint as B
        a, b = B.render(), B.render()
        # REG-3820's sibling (swept here from v3904's fix, v3905 pre-flight c): the LIVE blocks measure his disk (a store's size,
        # .orphan_cpu_sample.json rewritten by every doctor pass while laws run in parallel), so two renders differ there by
        # design. The question is the one --check asks, through blueprint.code_only - the ONE stripper - never its own copy
        strip = lambda t: "\n".join(l for l in B.code_only(t).splitlines()
                                    if not l.startswith("GENERATED") and "generated " not in l)
        self.assertEqual(strip(a), strip(b),
                         "render() is not deterministic — a clock or an unsorted dict is leaking "
                         "into the document, and every run would look like a stale blueprint")
        print("render() deterministic over %d bytes" % len(a))


RED_PROOF = [
    {
        "why": "REG-1637 - the #231 eye on v3531: an entry point types a line RANGE again, which the old pattern never saw",
        "file": "engine_index.json",
        "find": "      \"mode()/set_mode()/is_primary()\",\n",
        "replace": "      \"mode()/set_mode()/is_primary() :362-395\",\n",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - the index names console_settle.wait again, a function the file no longer has",
        "file": "engine_index.json",
        "find": "      \"wait_until_settled\",\n",
        "replace": "      \"wait\",\n",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - an entry point types a line number again, and drifts the day run_gates grows",
        "file": "engine_index.json",
        "find": "      \"test_the_set_pieces_carry_a_real_qlvl\",\n",
        "replace": "      \"test_the_set_pieces_carry_a_real_qlvl :3407\",\n",
        "matches": 1,
    },
    {
        "why": "the drift report is silenced, so a module on disk with no entry is dropped from "
               "the map without a word — the exact silent omission this law exists to prevent",
        "file": "blueprint.py",
        "find": '    drift = {"unindexed": sorted(set(on_disk) - set(curated)),',
        "replace": '    drift = {"unindexed": [],',
        "matches": 1,
    },
    {
        "why": "the engine section stops being rendered, so BLUEPRINT.md goes back to naming zero "
               "of the 178 modules and a reader greps a concept and concludes it does not exist",
        "file": "blueprint.py",
        "find": '    A("## THE ENGINE — every module, what it does, and what a reader gets wrong")',
        "replace": '    A("## (the engine section was removed)")',
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
