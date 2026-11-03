# -*- coding: utf-8 -*-
"""REG-3070's own near-miss - A PAGE FUNCTION IS DECLARED ONCE IN ITS SCRIPT; A SECOND DECLARATION WINS SILENTLY.

Building REG-3070, a new helper in the builder's block was named _cbSlotCats - the name of the builder's own category
reader thirty lines up. A function declaration is hoisted, and the LAST one in a scope wins for every caller: the
builder's tree, its hand catalogue and its node rows all started calling the new helper, with a worn slot's argument shape,
and four laws on the builder fell over (_cbBaseInCat: cat undefined). The JS syntax gate cannot see it - two declarations
of one name parse. This law reads every inline script of bible.html and lists each function declared at the script's top
two levels (a script's own top, and the top of its wrapping IIFE) more than once. The only twins today are named with
their reason; any other is refused. RED_PROOF below.
"""
import os
import re
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

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
# each one is declared inside its own intake handler (set tracker, uniques, runewords, ...), one per enclosing function -
# a twin by indentation only, never two in one scope
ALLOWED = {"downscale": "each AI intake handler declares its own downscale(file) inside itself"}


def _twins(src):
    out = []
    for m in re.finditer(r"<script([^>]*)>(.*?)</script>", src, re.S):
        attrs, body = m.group(1), m.group(2)
        if "application/json" in attrs:
            continue
        body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
        idm = re.search(r'id="([^"]+)"', attrs)
        where = idm.group(1) if idm else "the script at line %d" % (src.count("\n", 0, m.start()) + 1)
        for indent in ("", "  "):
            seen = {}
            for n in re.findall(r"(?m)^%sfunction\s+([\w$]+)\s*\(" % indent, body):
                seen[n] = seen.get(n, 0) + 1
            out.extend((where, n, c) for n, c in sorted(seen.items()) if c > 1)
    return out


class NoPageFunctionIsDeclaredTwice(unittest.TestCase):

    def test_every_page_function_is_declared_once(self):
        with open(PAGE, encoding="utf-8") as fh:
            src = fh.read()
        bad = ["%s: function %s declared %d times - the last one wins for every caller" % t for t in _twins(src)
               if t[1] not in ALLOWED]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_the_reader_sees_a_twin(self):
        page = '<script id="x">(function(){\n  function a(){}\n  function b(){}\n  function a(q){}\n})();</script>'
        self.assertEqual(_twins(page), [("x", "a", 2)], "the reader cannot see the twin it exists to catch")

    def test_the_allowed_twins_still_exist(self):
        with open(PAGE, encoding="utf-8") as fh:
            src = fh.read()
        names = {t[1] for t in _twins(src)}
        self.assertEqual(sorted(n for n in ALLOWED if n not in names), [],
                         "an allowed twin is gone - remove it from ALLOWED so the list stays true")


RED_PROOF = [
    {"why": "REG-3070's near-miss - the worn slot's category helper takes the builder's own name again",
     "file": "bible.html",
     "find": "  function _cbWornCats(worn){",
     "replace": "  function _cbSlotCats(worn){",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
