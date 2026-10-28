# -*- coding: utf-8 -*-
"""A HOP INTO THE BOARD FRAME MUST SHADOW `window`, NEVER ASSIGN IT.

v3209 joined the WRITE door to the board by hopping the JS context into the `#tvd-eng` iframe. It
did it with `window = _cw;`. **`window` is not an assignable binding** — in sloppy mode that write
is discarded with no error at all. So the hop "succeeded", changed nothing, and every line after it
went on asking the console shell.

MEASURED 2026-09-16: his console was running v3211, which CONTAINS v3209, and
`/api/chronicle_apply` still answered *"this page has no LSR, so a handoff note could not be
written into the right world"* — the exact refusal v3209 existed to end. Three restore attempts
were spent before the cause was found, while his ledger sat visibly wrong on screen.

⚠⚠ THE READ DOOR NEVER MADE THIS MISTAKE, AND THE DIFFERENCE IS THE WHOLE FIX. `board_ownership`
keeps a LOCAL `_ctx` and passes it as a PARAMETER NAMED `window` into an inner function, shadowing
the global for that scope. A parameter is assignable; the global is not. The two halves of one
channel were written days apart and only one of them was correct.

⚠⚠ A GATE THAT GREPPED FOR `tvd-eng` OR `_cw` WAS GREEN ACROSS THIS ENTIRE DEFECT — both strings
were present and the mechanism was dead. This pins the MECHANISM: shadow present, assignment
absent. It reads the JS by PARSING control_app.py's string literals, never by slicing a window of
source text around a guess. [[source-reading-guard]] [[the-unjoined-end]]
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
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

# `window` followed by a single `=` — an ASSIGNMENT. Not `==`, `===`, `!=`, `<=`, `>=`.
_ASSIGN = re.compile(r"(?<![=!<>])\bwindow\s*=(?!=)")
_SHADOW = re.compile(r"function\s*\(\s*window\b")


# The doors that REBIND the JS context into the board frame and then address board globals as
# `window.*`. Named, not inferred: plenty of code reaches into `#tvd-eng` to call one function on
# `contentWindow` directly and never rebinds anything — demanding a shadow from those would be a
# law about a string rather than about the mechanism, and the first version of this file did
# exactly that and failed 14 innocent literals. [[sabotage-is-usually-the-wrong-one]]
# ⚠ v3215 — `board_tick` JOINED THE LIST. It is the door the console UI actually presses and it
# was missing from the v3213 sweep entirely: an AST scan for 'tvd-eng' returned five doors and
# not this one, so every tick addressed the console shell. A named list only protects what it
# names, which makes leaving one out the quietest failure available. [[sweep-dont-ask]]
CONTEXT_HOPS = ("chronicle_apply", "board_ownership", "rw_restore", "board_mask",
                "owned_restore", "board_tick")


def _js_literals():
    """Every string constant in control_app.py that performs the #tvd-eng hop. -> [(where, text)]

    Parsed, not sliced. A regex over raw source would read a hop that spans concatenated literals
    as absent, which is the reading error this file exists to refuse.
    """
    src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and "tvd-eng" in node.value:
                out.append((fn.name, node.value))
    return out


class TestAHopShadowsTheWindow(unittest.TestCase):

    def setUp(self):
        self.hops = _js_literals()
        # ⚠ a denominator. If the parse ever stops finding the hops, this file must FAIL rather
        # than pass over nothing. [[zero-needs-a-denominator]]
        self.assertGreaterEqual(
            len(self.hops), 2,
            "found only %d #tvd-eng hop(s) in control_app.py — the reader has lost its reach, so "
            "its silence means nothing" % len(self.hops))

    def test_no_hop_assigns_the_global_window(self):
        """The live defect: `window=_cw` is discarded silently and the hop never happens."""
        bad = []
        for where, js in self.hops:
            for m in _ASSIGN.finditer(js):
                bad.append("%s: ...%s..." % (where, js[max(0, m.start() - 40):m.end() + 20]))
        self.assertEqual(
            bad, [],
            "a hop assigns the global `window`, which is a silent no-op — the hop will report "
            "success and reach nothing:\n  " + "\n  ".join(bad))

    def test_every_context_hop_shadows_window_as_a_parameter(self):
        """The fix, pinned positively: assignment absent is not the same as shadowing present."""
        seen = {}
        for where, js in self.hops:
            if where in CONTEXT_HOPS:
                seen.setdefault(where, False)
                if _SHADOW.search(js):
                    seen[where] = True
        # every named door must actually be FOUND, or the law is passing over a door it lost
        for door in CONTEXT_HOPS:
            self.assertIn(door, seen,
                          "%s no longer carries a #tvd-eng hop — either it was renamed or the "
                          "join was removed; this law cannot vouch for a door it cannot see" % door)
        missing = sorted(d for d, ok in seen.items() if not ok)
        self.assertEqual(
            missing, [],
            "these doors rebind the JS context into the board frame but never shadow `window` as "
            "a function parameter, so the code after the hop still addresses the console shell: %s"
            % ", ".join(missing))

    def test_the_write_door_is_one_of_them(self):
        """The door that actually failed him, named — so a rename cannot quietly drop it."""
        names = {w for w, _ in self.hops}
        self.assertIn("chronicle_apply", names,
                      "chronicle_apply no longer hops to the board at all; it was joined on "
                      "2026-09-16 after refusing every restore. Found: %s" % sorted(names))


class AHopTestsTheCapabilityTheCallNeeds(unittest.TestCase):
    """⚠⚠ EITHER-HANDLER IS NOT THE QUESTION THE CALL IS ASKING.

    v3215 joined `board_tick` to the frame hop and gated it on
    `toggleSetPiece OR toggleOwned` — on BOTH sides. So a page holding only `toggleOwned` kept a
    `set` tick in the wrong context and answered *"no toggleSetPiece"* about a window while the
    real one sat one frame away. Found by a cross-family look at v3215, reproduced in node before
    being believed: with a shell exposing only `toggleOwned` and a frame exposing only
    `toggleSetPiece`, a `set` tick reached the FRAME and never touched the shell.

    ⚠ AND THE MIRROR ERROR, SAME SHIP: `board_mask` is a READER, and the same pass made its hop
    demand `LSR.setItem`. A read-only LSR is a legitimate arrangement, and it would have been
    refused a read it could serve. That was a finding taken WHOLESALE instead of per-door — the
    capability fix was right for the restore doors and wrong there. [[review-after-ship]]
    """

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()

    def _js_of(self, fname):
        tree = ast.parse(self.src)
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef) and fn.name == fname:
                for n in ast.walk(fn):
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and "_ctx=_cw" in n.value:
                        return n.value
        return ""

    def test_board_tick_selects_on_the_handler_its_kind_needs(self):
        js = self._js_of("board_tick")
        self.assertTrue(js, "board_tick no longer carries a frame hop")
        self.assertIn("window[_need]", js,
                      "board_tick selects its frame without naming the handler the KIND requires, "
                      "so a set tick can stay on a page that only has toggleOwned")
        self.assertNotIn("typeof window.toggleSetPiece!=='function'&&typeof window.toggleOwned", js,
                         "the either-handler test is back — it answers a different question from "
                         "the one the call is about to ask")

    def test_a_reader_does_not_demand_a_writer(self):
        js = self._js_of("board_mask")
        self.assertTrue(js, "board_mask no longer carries a frame hop")
        self.assertNotIn("_cw.LSR.setItem", js,
                         "board_mask is a READER and its hop demands setItem, so a read-only LSR "
                         "is refused a read it could serve")

    def test_a_writer_does_demand_a_writer(self):
        """The opposite error, pinned so the fix above cannot be over-applied back."""
        js = self._js_of("owned_restore")
        self.assertTrue(js, "owned_restore no longer carries a frame hop")
        self.assertIn("_cw.LSR.setItem", js,
                      "owned_restore WRITES, so hopping into a context on getItem alone selects a "
                      "frame the write will then fail in")

RED_PROOF = [
    {"why": "v3209 - the write door hops by assigning the global window, a silent no-op in sloppy mode",
     "file": "tv/control_app.py",
     "find": "\"if(_cw&&(typeof _cw.chronicleApply==='function'||typeof _cw._D2R_PFX==='string'))\"\n          \"_ctx=_cw;}catch(_hop){}}\"",
     "replace": "\"if(_cw&&(typeof _cw.chronicleApply==='function'||typeof _cw._D2R_PFX==='string'))\"\n          \"window=_cw;}catch(_hop){}}\"",
     "matches": 1},
    {"why": "the write door picks the frame but never shadows window, so every line after the hop still asks the console shell",
     "file": "tv/control_app.py",
     "find": "\"return (function(window){try{\"\n          \"if(typeof window.chronicleApply==='function'){\"",
     "replace": "\"return (function(_unused){try{\"\n          \"if(typeof window.chronicleApply==='function'){\"",
     "matches": 1},
    {"why": "pre-v3209 - chronicle_apply does not hop into the board frame at all and refuses every restore",
     "file": "tv/control_app.py",
     "find": "\"try{var _fr=document.getElementById('tvd-eng');var _cw=_fr&&_fr.contentWindow;\"\n          \"if(_cw&&(typeof _cw.chronicleApply==='function'||typeof _cw._D2R_PFX==='string'))\"\n          \"_ctx=_cw;}catch(_hop){}}\"",
     "replace": "\"}\"",
     "matches": 1},
    {"why": "v3215 - board_tick selects its frame on either handler, so a set tick stays on a page that only has toggleOwned",
     "file": "tv/control_app.py",
     "find": "\"if(typeof window[_need]!=='function'){\"",
     "replace": "\"if(typeof window.toggleSetPiece!=='function'&&typeof window.toggleOwned!=='function'){\"",
     "matches": 1},
    {"why": "v3215 - board_mask, a reader, demands setItem, so a read-only LSR is refused a read it could serve",
     "file": "tv/control_app.py",
     "find": "if(_cw&&_cw.LSR&&_cw.LSR.getItem)_ctx=_cw;",
     "replace": "if(_cw&&_cw.LSR&&_cw.LSR.getItem&&_cw.LSR.setItem)_ctx=_cw;",
     "matches": 1},
    {"why": "owned_restore, a writer, hops on getItem alone and selects a frame the write then fails in",
     "file": "tv/control_app.py",
     "find": "if(_cw&&_cw.LSR&&_cw.LSR.getItem&&_cw.LSR.setItem)_ctx=_cw;}catch(_hop){}}",
     "replace": "if(_cw&&_cw.LSR&&_cw.LSR.getItem)_ctx=_cw;}catch(_hop){}}",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
