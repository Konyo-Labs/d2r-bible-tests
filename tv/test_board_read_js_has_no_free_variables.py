# -*- coding: utf-8 -*-
"""v2735 — THE LINE THAT KILLED HIS BACKUP FOR A DAY WHILE EVERY GATE STAYED GREEN.

v2731 was written to COMPLETE the automatic ledger backup: two of his six stores had never been
copied. It shipped with this in the board-read payload:

    "rwMadeFull:(dump?rwFull:null)});"

There is no JS variable named `dump`. The `dump_stores` flag is interpolated as a bare `true`/`false`
LITERAL twelve lines above (`if(%s){stores={}...`), so the name resolved to nothing, the whole read
threw `Can't find variable: dump`, and `_ledger_snapshot_once` refused every snapshot from that
moment on.

MEASURED on his live console the same day:

    ledgerBackup.writes  0
    ledgerBackup.why     "Can't find variable: dump"
    newest backup file   80 minutes old, still the pre-v2731 three-store shape

=== WHY NOTHING CAUGHT IT ===
`test_ledger_backup_covers_every_store` asserts the five stores are copied and passed throughout —
correctly, because it grades this SOURCE, and source is not a running board. CI was green on every
commit. The refusal existed in exactly one place: a string in `_LEDGER_BACKUP_STATE["why"]`, which
`/api/status` publishes and which nothing was reading. A loop that fails silently every ten minutes
looks identical to a loop with nothing to do. [[the-unjoined-end]] [[feedback-verify-not-proxy]]

=== WHAT THIS PINS ===
Python cannot typecheck a JavaScript string, but a free variable is not a type error — it is a name
used and never declared, and that IS checkable. This extracts the JS `board_ownership` actually
emits (statically, no window needed) and reports every identifier that is used, not declared, and
not a browser global.

⚠ PROVEN RED before being trusted, on the real defect and four sabotages:
    restore `(dump?rwFull:null)`      -> ['dump']         (the actual v2731 line)
    stores:stores   -> stores:storez  -> ['storez']
    dates:dates     -> dates:datez    -> ['datez']
    owner:owner     -> owner:ownerX   -> ['ownerX']
    boardLoaded:... -> boardLoadd     -> ['boardLoadd']
[[feedback-blind-fixture-green-gate]]
"""
import ast
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

SRC = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()

KEYWORDS = set("""var let const function return if else for while do try catch finally throw new
typeof instanceof in of delete void this null true false break continue switch case default
class extends super yield await async""".split())

#: Browser globals the board read is entitled to reach. ⚠ DELIBERATELY SHORT. Every name added here
#: is a name this law stops checking, so a wide allowlist is how a guard quietly stops guarding.
GLOBALS = set("""window document localStorage sessionStorage location navigator console JSON Object
Array String Number Boolean Math Date RegExp Error Promise Set Map parseInt parseFloat isNaN
undefined NaN Infinity encodeURIComponent decodeURIComponent setTimeout clearTimeout""".split())


def _strip_strings(js):
    """Blank every string literal so their contents are not read as code."""
    out, i, n = [], 0, len(js)
    while i < n:
        c = js[i]
        if c in "'\"":
            q = c
            i += 1
            while i < n and js[i] != q:
                if js[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append('""')
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _declared(js):
    d = set()
    for m in re.finditer(r'\bvar\s+([^;{}]+)', js):
        for part in m.group(1).split(','):
            nm = re.match(r'\s*([A-Za-z_$][\w$]*)', part)
            if nm:
                d.add(nm.group(1))
    for m in re.finditer(r'\bfunction\s*([A-Za-z_$][\w$]*)?\s*\(([^)]*)\)', js):
        if m.group(1):
            d.add(m.group(1))
        for p in m.group(2).split(','):
            p = p.strip()
            if re.match(r'^[A-Za-z_$][\w$]*$', p):
                d.add(p)
    for m in re.finditer(r'\bcatch\s*\(\s*([A-Za-z_$][\w$]*)', js):
        d.add(m.group(1))
    return d


def _used(js):
    u = set()
    for m in re.finditer(r'([.]?)\b([A-Za-z_$][\w$]*)\b(\s*:)?', js):
        if m.group(1):          # a property access — belongs to whatever is left of the dot
            continue
        if m.group(3):          # an object-literal KEY, not a read
            continue
        u.add(m.group(2))
    return u


def free_variables(js):
    """Names used and never declared. -> sorted list."""
    s = _strip_strings(js)
    return sorted(_used(s) - _declared(s) - KEYWORDS - GLOBALS)


def emitted_js(dump_stores):
    """The JS `board_ownership` actually builds. -> str

    Statically evaluated from the assignment's own expression, so no window and no live board are
    needed and the string graded is the string sent. ⚠ NOT a hand-copied duplicate of it — copying
    it here would make this law grade a fossil the moment the real one changed. [[copy-drift]]
    """
    tree = ast.parse(SRC)
    fns = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "board_ownership"]
    if not fns:
        return None
    asg = [n for n in fns[0].body
           if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "js" for t in n.targets)]
    if not asg:
        return None
    expr = asg[-1].value
    env = {"dump_stores": dump_stores, "sample": 0, "int": int}
    # v3888 (REG-3482 moved the board's store reader into the module constant _BOARD_STORE_JS) - a module-level STRING
    # constant the expression names is read from the same source, literally, never re-typed here: the string graded is
    # still the string sent. Anything that is not a literal stays unbound, so eval fails loudly rather than guessing.
    wanted = set(n.id for n in ast.walk(expr) if isinstance(n, ast.Name)) - set(env)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and getattr(node.targets[0], "id", None) in wanted:
            try:
                env[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return eval(compile(ast.Expression(expr), "<board-js>", "eval"), env)


class BoardReadJsHasNoFreeVariables(unittest.TestCase):

    def test_the_guard_can_reach_the_javascript_AT_ALL(self):
        """⚠ THE VACUITY GUARD, AND IT IS LOAD-BEARING HERE.

        If extraction fails, `free_variables("")` is `[]` and every law below passes having examined
        nothing — a green that means "I could not look". Exactly the shape this repo keeps finding.
        [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
        """
        for dump in (True, False):
            js = emitted_js(dump)
            self.assertIsNotNone(
                js, "the board-read JS could not be extracted (dump_stores=%s). board_ownership no "
                    "longer assigns a single `js`, so this law is grading nothing — fix the "
                    "extraction before trusting a green here." % dump)
            self.assertGreater(
                len(js), 2000,
                "the extracted JS is %d chars, far short of the ~3.5k the real read is. A truncated "
                "extraction has few names in it and would pass by having nothing to check."
                % len(js))
            self.assertIn("JSON.stringify({ok:true", js,
                          "the extracted JS does not contain the payload it exists to build")

    # ── ⚠⚠ THE LAW ────────────────────────────────────────────────────────────────────────────
    def test_no_free_variables_in_either_mode(self):
        for dump in (True, False):
            js = emitted_js(dump)
            free = free_variables(js)
            self.assertEqual(
                [], free,
                "the board-read JS uses %s without declaring %s (dump_stores=%s).\n\n"
                "This is the v2731 defect exactly: `rwMadeFull:(dump?rwFull:null)` referenced a "
                "`dump` variable that never existed, because dump_stores is interpolated as a bare "
                "true/false LITERAL. The name resolved to nothing, the WHOLE read threw "
                "'Can't find variable: dump', and his automatic ledger backup wrote zero files for "
                "a day while every gate stayed green.\n"
                "A free variable here does not degrade one field — it kills the entire board read, "
                "and everything downstream reports an honest refusal about a defect one line long."
                % (free, "it" if len(free) == 1 else "them", dump))

    def test_BOTH_modes_are_graded_not_only_the_dumping_one(self):
        """The defect shipped inside a `dump ?` conditional. Grading one mode is how a conditional
        bug survives — and both branches of `if(%s)` produce genuinely different source."""
        a, b = emitted_js(True), emitted_js(False)
        self.assertNotEqual(a, b, "dump_stores changes nothing in the emitted JS, so grading both "
                                  "modes is grading one thing twice — the flag or this law is wrong")

    # ── the scanner must not be silently toothless ────────────────────────────────────────────
    def test_the_scanner_finds_a_planted_free_variable(self):
        """⚠ A scanner that returns [] because it cannot parse is indistinguishable from a clean
        one. This plants the real defect back and requires it to be seen. [[feedback-suspect-the-instrument]]"""
        js = emitted_js(True).replace("rwMadeFull:rwFull", "rwMadeFull:(dump?rwFull:null)", 1)
        self.assertIn("dump?", js, "the plant did not apply — this check proved nothing")
        self.assertIn("dump", free_variables(js),
                      "the scanner did not report `dump` when the actual v2731 line was planted "
                      "back. It is not measuring what it claims to measure.")

    def test_the_scanner_does_not_confuse_a_property_for_a_free_name(self):
        """`a.zzz` and `{zzz: 1}` are not reads of a variable named zzz. A scanner that flagged them
        would be noisy, and a noisy gate gets disabled — which is a slower way to have no gate."""
        self.assertEqual([], free_variables("var a={};a.zzzUnique;var o={zzzKey:1};"))
        self.assertEqual(["zzzBare"], free_variables("var a={};a.zzzUnique;zzzBare;"),
                         "a genuine free read next to a property access was missed")

    def test_the_globals_allowlist_stays_small(self):
        """Every name here is a name this law stops checking. Growth is how a guard retires quietly."""
        self.assertLessEqual(
            len(GLOBALS), 40,
            "the browser-global allowlist has grown to %d. Each entry is an exemption; widening it "
            "to silence a failure is how this law stops being one." % len(GLOBALS))


RED_PROOF = [
    {
        'why': 'Renaming the JS `var storeEmptied=null;` declaration inside board_ownership\'s emitted script leaves the later `storeEmptied={at:...}` assignment and the `storeEmptied:storeEmptied` payload read pointing at a name that is never declared — the exact v2731 shape (`rwMadeFull:(dump?rwFull:null)`) that made the whole board read throw \'Can\'t find variable: dump\' and stopped his automatic ledger backup for a day while every gate stayed green. It deletes a real declaration in the code the law grades, not a comment, a message string or a shared constant.  MEASURED: untampered OK — Ran 6 tests in 1.42s, all ok (python3 tv/test_board_read_js_has_no_free_variables.py); tampered (all 1) FAILED (failures=1) — Ran 6 tests; only test_no_free_variables_in_either_mode red: "Lists ; reddened law test_board_read_js_has_no_free_variables.BoardReadJsHasNoFreeVariables; ALONE FAILED alone — python3 -m unittest test_board_read_js_has_no_free_variables.BoardReadJsHasNoFreeVariables.test.',
        'file': 'control_app.py',
        'find': 'var storeEmptied=null;',
        'replace': 'var storeEmptiedZ=null;',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
