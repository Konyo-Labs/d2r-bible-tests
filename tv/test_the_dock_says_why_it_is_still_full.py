# -*- coding: utf-8 -*-
"""A BUTTON THAT CORRECTLY DOES NOTHING MUST SAY SO, OR IT READS AS BROKEN.

Konyo, twice: *"its not even sorting them.. only some"*, and at a screenshot of the Vault,
*"stlll the vault"*. The dock showed a COUNT and an **Auto-Sort to Mules** button. He pressed it,
nothing moved, and nothing on screen said why.

MEASURED on his board, 2026-09-17: of 219 in the pool, **173 are filed and all 46 unsorted carry
exactly one suggestion — `__throwout`**. Auto-Sort will not act on that, because throwing his
items away is his decision and never automatic. So the button correctly does nothing and the dock
correctly keeps them.

**Both halves were right and the screen said neither.** A number with no reason beside a button
that does nothing is indistinguishable from a broken sorter — which is exactly what he reported,
twice. [[zero-needs-a-denominator]] [[the-unjoined-end]]

⚠ This runs the SHIPPED block in node against a stubbed `suggestMule`, rather than asserting the
text is present. The sentence is not the law; what the sentence is derived FROM is.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

BIBLE = os.path.join(REPO, "bible.html")


def _block():
    """The shipped `_why` computation, lifted whole. -> str | None"""
    with io.open(BIBLE, encoding="utf-8", errors="replace") as f:
        src = f.read()
    i = src.find("        var _why = '';")
    if i < 0:
        return None
    j = src.find("dbar.innerHTML=", i)
    return src[i:j] if j > 0 else None


class TestTheDockSaysWhyItIsStillFull(unittest.TestCase):

    def setUp(self):
        self.blk = _block()
        self.assertIsNotNone(self.blk, "the dock's reason block is gone — re-anchor this gate")

    def _run(self, names, suggest):
        """Run the shipped block with a stubbed suggestMule. -> the _why string it produced."""
        if shutil.which("node") is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        d = tempfile.mkdtemp(prefix="dockwhy_")
        self.addCleanup(shutil.rmtree, d, True)
        js = ("var unsorted = %s;\n"
              "var _SUG = %s;\n"
              "function suggestMule(n){ return _SUG[n] === undefined ? null : _SUG[n]; }\n"
              % (json.dumps(names), json.dumps(suggest))
              + self.blk + "\nconsole.log(JSON.stringify(_why));\n")
        p = os.path.join(d, "b.js")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run(["node", p], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "the shipped block would not run:\n%s"
                         % r.stderr.decode("utf-8", "replace")[:500])
        return json.loads(r.stdout.decode("utf-8", "replace").strip())

    # ── HIS ACTUAL STATE ─────────────────────────────────────────────────────────────────────
    def test_all_discard_says_auto_sort_will_not_throw_things_away(self):
        """★ HIS BOARD, REPRODUCED: 46 unsorted, every one a `__throwout` suggestion."""
        names = ["item%d" % i for i in range(46)]
        why = self._run(names, {n: {"id": "__throwout"} for n in names})
        self.assertTrue(why, "the dock says nothing at all while every item is a discard — which "
                              "is the state he reported twice as a broken sorter")
        self.assertIn("discard", why, "the reason does not name the suggestion: %r" % why)
        self.assertIn("will not throw", why,
                      "it does not say the button is DECLINING rather than failing: %r" % why)

    def test_a_mixed_dock_names_the_shapes_instead(self):
        """When some could be filed, the blanket sentence would be false."""
        names = ["a", "b", "c", "d"]
        why = self._run(names, {"a": {"id": "__throwout"}, "b": {"id": "__throwout"},
                                "c": {"id": "uni-armor"}, "d": {"id": "sets-rest"}})
        self.assertNotIn("will not throw", why,
                         "it claims every item is a discard while two could be filed — that would "
                         "excuse a sorter that really is leaving work undone: %r" % why)
        self.assertIn("discard", why, "the discard share is not reported: %r" % why)
        self.assertIn("2", why, "the counts are missing, so the reason is not a measurement: %r" % why)

    # ── UNKNOWN IS NOT A CLAIM ──────────────────────────────────────────────────────────────
    def test_no_sorter_means_no_sentence(self):
        """★ If `suggestMule` is not reachable the dock must say NOTHING, not guess."""
        if shutil.which("node") is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        d = tempfile.mkdtemp(prefix="dockwhy_")
        self.addCleanup(shutil.rmtree, d, True)
        js = ("var unsorted = ['a','b'];\n" + self.blk
              + "\nconsole.log(JSON.stringify(_why));\n")
        p = os.path.join(d, "b.js")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run(["node", p], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "with no suggestMule the block THREW instead of staying quiet:\n%s"
                         % r.stderr.decode("utf-8", "replace")[:400])
        self.assertEqual(json.loads(r.stdout.decode("utf-8", "replace").strip()), "",
                         "it produced a reason with no sorter to derive one from")

    def test_an_empty_dock_says_nothing(self):
        self.assertEqual(self._run([], {}), "",
                         "an empty dock still printed a reason, which would sit under a count of 0")

    def test_a_sorter_that_raises_does_not_take_the_bar_down(self):
        """The dock must render even when the sorter is broken — it is his only way back."""
        if shutil.which("node") is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        d = tempfile.mkdtemp(prefix="dockwhy_")
        self.addCleanup(shutil.rmtree, d, True)
        js = ("var unsorted = ['a','b'];\n"
              "function suggestMule(n){ throw new Error('boom'); }\n"
              + self.blk + "\nconsole.log(JSON.stringify(_why));\n")
        p = os.path.join(d, "b.js")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run(["node", p], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "a throwing sorter took the dock bar with it:\n%s"
                         % r.stderr.decode("utf-8", "replace")[:400])
        why = json.loads(r.stdout.decode("utf-8", "replace").strip())
        self.assertNotIn("will not throw", why,
                         "a sorter that raised produced a confident verdict: %r" % why)

    def test_ONE_bad_item_does_not_silence_the_whole_reason(self):
        """★ WHAT THE PER-ITEM GUARD IS ACTUALLY FOR, and my first proof could not see it.

        Removing the inner `try` left the suite green, because the OUTER catch still stops the
        block throwing — so "it did not crash" proves nothing about the inner guard. Its real job
        is that ONE item whose suggestion raises must not take the other 45 with it. Without it,
        a single bad name turns a measured reason into silence, and silence is what he already
        read as a broken sorter. [[sabotage-is-usually-the-wrong-one]]"""
        if shutil.which("node") is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        d = tempfile.mkdtemp(prefix="dockwhy_")
        self.addCleanup(shutil.rmtree, d, True)
        names = ["ok%d" % i for i in range(5)] + ["poison"]
        js = ("var unsorted = %s;\n" % json.dumps(names)
              + "function suggestMule(n){ if (n === 'poison') throw new Error('boom');\n"
                "  return { id: '__throwout' }; }\n"
              + self.blk + "\nconsole.log(JSON.stringify(_why));\n")
        p2 = os.path.join(d, "b.js")
        with io.open(p2, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run(["node", p2], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "one throwing item took the whole bar down:\n%s"
                         % r.stderr.decode("utf-8", "replace")[:400])
        why = json.loads(r.stdout.decode("utf-8", "replace").strip())
        self.assertTrue(why,
                        "ONE item whose suggestion raised silenced the reason for all six — the "
                        "other five are perfectly readable and their verdict was thrown away")
        self.assertIn("discard", why,
                      "the five readable items are not reported: %r" % why)

    # ── A CLASS NOBODY STYLES IS A FLAG NOBODY CAN SEE ──────────────────────────────────────
    def test_the_reason_has_a_css_rule(self):
        with io.open(BIBLE, encoding="utf-8", errors="replace") as f:
            src = f.read()
        i = src.find(".vdb-why{")
        self.assertGreater(i, 0, "the reason's class has no rule, so it renders unstyled — the "
                                 "shape sh-chip-st and sh-chip-stunk both shipped in")
        self.assertIn("color", src[i:src.find("}", i) + 1])

RED_PROOF = [
    {"why": "the dock's all-discard reason claims every item is a discard while some could be filed (a sorter leaving work undone is excused)",
     "file": "bible.html",
     "find": "            if (_keys.length === 1 && _keys[0] === '__throwout'){\n",
     "replace": "            if (_keys.length && _h['__throwout']){\n",
     "matches": 1, "needs": "node"},
    {"why": "one item whose suggestion raises silences the dock's reason for every other item",
     "file": "bible.html",
     "find": "              try { sg = suggestMule(nm); } catch (e) { sg = null; }\n",
     "replace": "              sg = suggestMule(nm);\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
