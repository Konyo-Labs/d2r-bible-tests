# -*- coding: utf-8 -*-
"""#173 (REG-2938) - NO PYTHON DOOR WRITES `d2r_owned` WITHOUT THE RECEIPT DOOR. Moved out of
test_every_owned_door_writes_provenance - verbatim but for one instrument fix: a function's docstring no longer
counts as the JS it sends (see the census).

control_app sends the board JS; any function whose strings send a setItem('d2r_owned') must also send
window._ownedAdd(, or the vault grows with no receipt (M4 of the review of 77d8d8b5: owned_restore wrote a union list
straight into the store). The census reads EVERY shipped .py in tv/ - the folder is the denominator, so a new module
that sends a bare write cannot hide. That listing is why this case lives alone: a law that lists a directory itself
cannot have its proofs saved (heart2: "what it reads is decided at run time"), and inside the owned-door law it made
all 32 of that law's proofs re-run on every push. Here it is one cheap case, listed in tv/unkeyable_laws.json on
purpose. [[the-unjoined-end]] [[regression-guard]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


class NoPythonDoorWritesOwnedBare(unittest.TestCase):

    def test_no_python_door_writes_owned_without_the_door(self):
        """control_app sends the board JS; any function that sends a setItem('d2r_owned') must also send _ownedAdd."""
        import ast
        bad = []
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_") or fn.startswith("."):
                continue
            try:
                with io.open(os.path.join(HERE, fn), encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                # #173 - a DOCSTRING is prose, not JS the door sends: owned_restore's own docstring spells
                # "window._ownedAdd(name, ...)", which kept this census green with the call itself removed (its
                # red-proof below came back GREEN until the docstrings were left out).
                doc = set(id(d.body[0].value) for d in ast.walk(node)
                          if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and d.body
                          and isinstance(d.body[0], ast.Expr) and isinstance(d.body[0].value, ast.Constant)
                          and isinstance(d.body[0].value.value, str))
                strs = "".join(n.value for n in ast.walk(node)
                               if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc)
                if "setItem('d2r_owned'" in strs and "window._ownedAdd(" not in strs:
                    bad.append("%s:%s" % (fn, node.name))
        self.assertEqual([], bad, "a console door writes d2r_owned on the board with no receipt: %r" % bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "M4 - owned_restore writes d2r_owned and no longer calls the receipt door: a restore grows the vault "
               "with no provenance",
        "file": "control_app.py",
        "find": "          \"try{var _pr=window._ownedAdd(added[k],{source:'ledger-restore',by:'owned_restore',ts:TS,\"\n",
        "replace": "          \"try{var _pr=void(0,{source:'ledger-restore',by:'owned_restore',ts:TS,\"\n",
        "matches": 1,
    },
]
