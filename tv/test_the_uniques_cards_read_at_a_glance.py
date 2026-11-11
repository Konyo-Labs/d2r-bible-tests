# -*- coding: utf-8 -*-
"""#198 (REG-3673) - THE UNIQUES TAB'S QUICK WINS AND BEST RUNS READ AT A GLANCE.

His words, 11-10: "for the uniques section i want best wins/quick wins alot bigger like this for example" (his reference: each
place's numbers large and bold over their labels, a big portrait) and "this is nicer for the other section for best runs" (a big
portrait, a round rank badge, the run's name in the display caps, its numbers large). MEASURED on the render at 1440 before: Quick
wins' four numbers at 13px over 10px labels beside a 72px tile; a Best runs card with a 48px portrait and its name at ~18px.

Pinned as the LAW, not the pixel: the card's own size tokens (bible.html, scoped to #tab-funi) are resolved against :root at every
width step, and
  * Quick wins: a number reads at least 2x its label at full width and at least 1.6x at every narrower step, the number is at
    least the display size at full width, and the number, the label and the name are drawn FROM those tokens;
  * Best runs: the run's name is at least 1.2x the display size and its numbers at least the display size at full width, the
    portrait is at least 100px, and the name and the numbers are drawn from those tokens.
The pixels are tv/render_check.py's targets quick-wins and best-runs. RED_PROOF below. [[visual-regression-detector]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _page():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _root_px(src):
    root = re.search(r":root\{([^}]*)\}", src).group(1)
    return {k: float(v) for k, v in re.findall(r"(--fs-[a-z]+):(\d+(?:\.\d+)?)px", root)}


def _resolve(expr, base, local):
    """'calc(var(--fs-display)*1.3)' | 'var(--fs-title)' | 'var(--fs-qw-x)' -> px"""
    expr = expr.strip()
    m = re.fullmatch(r"calc\(var\((--[a-z0-9-]+)\)\*(\d+(?:\.\d+)?)\)", expr)
    if m:
        return _resolve("var(%s)" % m.group(1), base, local) * float(m.group(2))
    m = re.fullmatch(r"var\((--[a-z0-9-]+)\)", expr)
    if m:
        k = m.group(1)
        if k in local:
            return _resolve(local[k], base, local)
        return base[k]
    raise AssertionError("a size the law cannot read: %r" % expr)


def _steps(src, selector, prefix):
    """[(label, {token: px})] - the base rule, then each @media step, each step inheriting the one before"""
    base = _root_px(src)
    rules = re.findall(re.escape(selector) + r"\{(%s[^}]*)\}" % re.escape(prefix), src)
    if not rules:
        raise AssertionError("no %s{%s...} rule - the card's tokens are gone" % (selector, prefix))
    out, local = [], {}
    for i, body in enumerate(rules):
        for k, v in re.findall(r"(--fs-[a-z0-9-]+):([^;]+)", body):
            local[k] = v
        out.append(("base" if i == 0 else "step %d" % i, {k: _resolve(v, base, local) for k, v in local.items()}))
    return out, base


class QuickWinsReadsAtAGlance(unittest.TestCase):
    def setUp(self):
        self.src = _page()
        self.steps, self.base = _steps(self.src, "#tab-funi .qw-card", "--fs-qw-num")

    def test_a_number_reads_large_over_its_label_at_every_width(self):
        self.assertGreaterEqual(len(self.steps), 2, "PREMISE: Quick wins has a base size and at least one narrower step")
        for label, t in self.steps:
            with self.subTest(step=label):
                ratio = t["--fs-qw-num"] / t["--fs-qw-sub"]
                floor = 2.0 if label == "base" else 1.6
                self.assertGreaterEqual(ratio, floor, "%s: a number is %.2fx its label (needs %.1fx) - it reads like its "
                                                      "own caption again" % (label, ratio, floor))
        self.assertGreaterEqual(self.steps[0][1]["--fs-qw-num"], self.base["--fs-display"],
                                "at full width a Quick wins number is smaller than the display size")

    def test_the_number_the_label_and_the_name_are_drawn_from_those_tokens(self):
        for sel, tok in (("#tab-funi .qw-card .qw-stat b", "--fs-qw-num"), ("#tab-funi .qw-card .qw-stat .qw-sub", "--fs-qw-sub"),
                         ("#tab-funi .qw-card .qw-name", "--fs-qw-name")):
            with self.subTest(sel=sel):
                self.assertEqual(self.src.count(sel + "{font-size:var(%s)" % tok), 1,
                                 "%s is not drawn from %s - the token can be big while the element is not" % (sel, tok))


class BestRunsReadsAtAGlance(unittest.TestCase):
    def setUp(self):
        self.src = _page()
        self.steps, self.base = _steps(self.src, "#tab-funi .forge-sec-pipe", "--fs-br-title")

    def test_the_name_and_the_numbers_are_large_at_full_width(self):
        t = self.steps[0][1]
        self.assertGreaterEqual(t["--fs-br-title"], 1.2 * self.base["--fs-display"], "a run's name is not in the display caps")
        self.assertGreaterEqual(t["--fs-br-num"], self.base["--fs-display"], "a run's numbers are not large")

    def test_the_portrait_is_large(self):
        m = re.search(r"#tab-funi \.forge-sec-pipe \.f-pipe \.f-cardart-hd\{flex:0 0 (\d+)px;width:(\d+)px;height:(\d+)px", self.src)
        self.assertIsNotNone(m, "the Best runs portrait rule is gone")
        self.assertGreaterEqual(min(int(m.group(2)), int(m.group(3))), 100, "the Best runs portrait is small again")

    def test_the_name_and_the_numbers_are_drawn_from_those_tokens(self):
        for sel, tok in (("#tab-funi .forge-sec-pipe .f-pipe .f-atomact .f-rwbig", "--fs-br-title"),
                         # v3898 - the run's numbers stand on the right as stats (his 11-11 15:25)
                         ("#tab-funi .forge-sec-pipe .f-pipe .f-runstats .qw-stat b", "--fs-br-num"),
                         ("#tab-funi .forge-sec-pipe .f-pipe .f-runstats .qw-stat .qw-sub", "--fs-br-label")):
            with self.subTest(sel=sel):
                self.assertEqual(self.src.count(sel + "{font-size:var(%s)" % tok), 1,
                                 "%s is not drawn from %s" % (sel, tok))

    def test_the_numbers_stand_on_the_right_as_quick_wins_does(self):
        """v3898 (his 11-11 15:25: "its using only the left side the whole right is blank ... the data like hour can be on the
        right side like it is on the quickwins") - a two-column card body, the stats in the right column, built by _qwStat"""
        self.assertIn("#tab-funi .forge-sec-pipe .f-pipe .f-cardtitle{display:grid;grid-template-columns:minmax(0,1fr) auto;",
                      self.src, "the Best runs card body is one column again - the right half is blank")
        self.assertIn("#tab-funi .forge-sec-pipe .f-pipe .f-cardtitle > .f-runstats{grid-column:2;", self.src,
                      "the run's numbers are not in the right column")
        import js_strip
        code = js_strip.strip_js_comments(self.src)
        self.assertEqual(code.count("+'<div class=\"f-runstats\">'+_qwStat(String(r.items.length), 'of your missing uniques', 'br-drops')"), 1,
                         "the Best runs card does not build its numbers as Quick wins' stats")
        self.assertEqual(code.count("_qwStat('~' + c.t, 'to find ' + c.word, 'br-hours'"), 1,
                         "the run's clock is not a stat - or it is printed twice (v1740 one number per farm)")


RED_PROOF = [
    {"why": "v3898 (his 11-11) - the Best runs numbers fall back into the left column and the right half is blank again",
     "file": "bible.html",
     "find": "#tab-funi .forge-sec-pipe .f-pipe .f-cardtitle > .f-runstats{grid-column:2;",
     "replace": "#tab-funi .forge-sec-pipe .f-pipe .f-cardtitle > .f-runstats{grid-column:1;",
     "matches": 1},
    {"why": "#198 (REG-3673) - Quick wins' numbers are set at the body size again, the size of their own labels",
     "file": "bible.html",
     "find": "#tab-funi .qw-card{--fs-qw-num:calc(var(--fs-display)*1.3);",
     "replace": "#tab-funi .qw-card{--fs-qw-num:var(--fs-body);",
     "matches": 1},
    {"why": "#198 (REG-3673) - the Quick wins number stops reading its token (the token stays big, the number does not)",
     "file": "bible.html",
     "find": "#tab-funi .qw-card .qw-stat b{font-size:var(--fs-qw-num);",
     "replace": "#tab-funi .qw-card .qw-stat b{font-size:var(--fs-body);",
     "matches": 1},
    {"why": "#198 (REG-3673) - the Best runs portrait is 48px again",
     "file": "bible.html",
     "find": "#tab-funi .forge-sec-pipe .f-pipe .f-cardart-hd{flex:0 0 112px;width:112px;height:112px;",
     "replace": "#tab-funi .forge-sec-pipe .f-pipe .f-cardart-hd{flex:0 0 48px;width:48px;height:48px;",
     "matches": 1},
    {"why": "#198 (REG-3673) - a run's name is no longer in the display caps",
     "file": "bible.html",
     "find": "#tab-funi .forge-sec-pipe{--fs-br-title:calc(var(--fs-display)*1.25);",
     "replace": "#tab-funi .forge-sec-pipe{--fs-br-title:var(--fs-title);",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
