# -*- coding: utf-8 -*-
"""v3179 — A ROW THAT SAYS "NOTHING IS KNOWN" MAY NOT RENDER AS A FAULT.

HIS ORDER, 2026-09-15, reading the state panel: *"make it updated to whats needed and everythin
should be reading healthy if its not missing and those that are are being fixed ... so update the
others so they dont show those things so its honest"*.

MEASURED, and he was right: `tooltip finder` returned MISSING while its own sentence read "the
finder has never been asked — no frame has been put through it, so nothing is known about it
either way". A lane nobody has exercised is not a broken lane. Worse, MISSING feeds WHAT NEEDS
YOU, so an unexercised lane was inflating the one number he acts on.

★ THIS IS THE CONSOLE'S OLDEST DOCTRINE, ENFORCED MECHANICALLY INSTEAD OF BY MEMORY:
    0     = measured, and it is zero
    None  = nobody looked
  Collapsing them is a lie with no author. The console has corrected that confusion by hand
  repeatedly — UNIQUES SYNCED over 0/403, the both-need column refusing rather than claiming 0,
  a dead fetch made to say UNKNOWN rather than paint parity, and v3177's decoded-empty mask.
  Each was found by a person noticing. This one is found by the file.

⚠ PARSED, NEVER GREPPED. A grep would fire on the word "unknown" inside a comment, or miss a
sentence split across concatenated string parts. This walks the AST for `return MISSING, <str>`
and joins the pieces the way Python does. [[source-reading-guard]] [[unknown-stays-unknown]]
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass

#: phrases that ADMIT the row could not find out. A row saying any of these is UNKNOWN by its own
#: account, whatever constant it returns.
ADMITS_UNKNOWN = (
    "nothing is known",
    "never been asked",
    "has not been asked",
    "nobody looked",
    "could not find out",
)

DOCTORS = ("console_doctor.py", "health_engine.py", "vault_doctor.py", "chronicle_doctor.py")


def _joined(node):
    """The literal text of a string expression, including implicit concatenation and +."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _joined(node.left) + _joined(node.right)
    if isinstance(node, ast.JoinedStr):
        return "".join(_joined(v) for v in node.values if isinstance(v, (ast.Constant, ast.BinOp)))
    return ""


def _offenders(path):
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    out = []
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Return) or not isinstance(n.value, ast.Tuple):
            continue
        if len(n.value.elts) < 2:
            continue
        head = n.value.elts[0]
        if not (isinstance(head, ast.Name) and head.id == "MISSING"):
            continue
        text = _joined(n.value.elts[1])
        hit = [p for p in ADMITS_UNKNOWN if p in text.lower()]
        if hit:
            out.append((os.path.basename(path), n.lineno, hit[0], text[:110]))
    return out


class AMissingRowNeverClaimsItDoesNotKnow(unittest.TestCase):

    def test_no_doctor_returns_MISSING_while_admitting_it_never_looked(self):
        bad = []
        for name in DOCTORS:
            p = os.path.join(HERE, name)
            if os.path.isfile(p):
                bad += _offenders(p)
        self.assertEqual(
            bad, [],
            "a row renders as a FAULT while its own sentence says it never looked. That is the "
            "one confusion this console exists to prevent, and MISSING feeds WHAT NEEDS YOU, so "
            "it also inflates the number he acts on. Return UNKNOWN instead:\n  "
            + "\n  ".join("%s:%d says %r — %s" % b for b in bad))

    def test_the_guard_can_actually_see_a_violation(self):
        """A guard that cannot find a planted offender is measuring nothing — so plant one in a
        throwaway module and require it to be caught. [[feedback-blind-fixture-green-gate]]"""
        import tempfile
        src = ("MISSING = 'missing'\n"
               "def check():\n"
               "    return MISSING, ('this lane has ' 'never been asked, so nothing is known')\n")
        fd, p = tempfile.mkstemp(prefix=".guardprobe_", suffix=".py", dir=HERE)
        try:
            with io.open(fd, "w", encoding="utf-8") as fh:
                fh.write(src)
            found = _offenders(p)
        finally:
            try:
                os.unlink(p)
            except OSError:
                pass
        self.assertTrue(found, "the guard cannot see a planted violation, so its green means "
                               "nothing")
        # the probe sentence contains BOTH phrases and _offenders reports the first match in
        # ADMITS_UNKNOWN order — pin that it named A real phrase, not which one won the race.
        self.assertIn(found[0][2], ADMITS_UNKNOWN)

RED_PROOF = [
    {"why": "v3179 - the tooltip finder nobody has asked renders as a FAULT in WHAT NEEDS YOU while its own sentence says nothing is known",
     "file": "tv/console_doctor.py",
     "find": "        return UNKNOWN, (\"the finder has never been asked",
     "replace": "        return MISSING, (\"the finder has never been asked",
     "matches": 1},
    {"why": "a router that would not answer is counted as a broken lane, inflating the number he acts on",
     "file": "tv/console_doctor.py",
     "find": "            return UNKNOWN, \"the router would not answer, so nothing is known about banking\"",
     "replace": "            return MISSING, \"the router would not answer, so nothing is known about banking\"",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
