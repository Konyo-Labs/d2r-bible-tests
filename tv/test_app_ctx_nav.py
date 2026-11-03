"""v2471 — THE PAGE MAY ONLY HIDE ITS OWN NAV WHEN SOMETHING ELSE IS PROVABLY CARRYING IT.

⚠ THE DEFECT THIS EXISTS FOR. Konyo, 2026-09-03, with a screenshot of an empty header band:
"i cant see any tabs... something is bugged". Measured on his build: `.tabs` computed
`display:none`, 0 of 19 tab buttons laid out, body carrying `app-ctx engine-driven`.

`?engine=1` is written in exactly ONE place in this repo — the `#tvd-eng` IFRAME in
tv/control_ui.html — and the rule it arms is:

    body.app-ctx.engine-driven .tabs { display:none !important }

whose own comment states the theory: "console header is the one clickable rail". True inside the
shell. Open that same URL as a top-level window and the flag still arms, the rail is not there,
and the document hides its navigation in favour of nothing. The flag was a CLAIM ABOUT CONTEXT and
nothing ever checked the context. [[the-unjoined-end]]

TWO LAWS, both pinned here, neither pinned to a number or a roster:

  1. The `engine-driven` CLASS is only added when the document is genuinely framed. Every site
     that adds it must test `window.top !== window.self`. (`ENGINE_DRIVEN` the VARIABLE is
     deliberately NOT gated — it also decides whether this page arms its own intake poll, and
     loosening that would let a top-level pane double-arm against the control process.)

  2. Every tab re-shown in app context lives in `.tabs-workshop`. `body.app-ctx .tabs-data
     {display:none}` hides the container holding `main` + the HUNT and LORE clusters, which would
     otherwise paint as empty captioned boxes. That is correct ONLY while law 2 holds — so if
     someone re-shows a data tab by name, this goes red instead of the tab silently vanishing,
     which is the exact trap the v2084 comment in bible.html warns about.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# this file prints ⚔/🪜 in its failure messages; without this it CRASHES WHILE REPORTING on a
# non-UTF-8 console, so a clean tree would exit non-zero for a reason that is not the code
from console_safe import enable  # noqa: E402

enable()
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
SHELL = os.path.join(HERE, "control_ui.html")


def _src():
    # anchored on __file__, never on the working directory — a zero result must be about the file
    return io.open(BIBLE, encoding="utf-8").read()


#: Every way JavaScript can put a class on an element. The point of the list is that the guard
#: must not be tied to ONE of them — that was the hole the v2471 review walked straight through.
_WRITE_SHAPES = (
    (r"classList\s*\.\s*add\s*\([^)]*['\"]engine-driven['\"]", "classList.add"),
    (r"classList\s*\.\s*toggle\s*\([^)]*['\"]engine-driven['\"]", "classList.toggle"),
    (r"className\s*\+?=\s*[^;]*engine-driven", "className assignment"),
    (r"setAttribute\s*\(\s*['\"]class['\"][^)]*engine-driven", "setAttribute('class')"),
    (r"classList\s*\[[^\]]*\]\s*\([^)]*['\"]engine-driven['\"]", "classList[computed]"),
)


def _script_regions(src):
    """(start, end) of every inline <script> body — the class literal also lives in CSS."""
    out = []
    for m in re.finditer(r"<script\b[^>]*>", src):
        end = src.find("</script>", m.end())
        if end > 0:
            out.append((m.end(), end))
    return out


def _class_write_sites(src):
    """-> [(pos, how)] every JS site that WRITES the engine-driven class, by any mechanism."""
    regions = _script_regions(src)
    sites = []
    for pat, how in _WRITE_SHAPES:
        for m in re.finditer(pat, src):
            if any(a <= m.start() < b for a, b in regions):
                sites.append((m.start(), how))
    return sorted(set(sites))


def _controlling_condition(src, pos):
    """The condition that decides whether the write at `pos` happens. -> str | None

    Two shapes carry a condition: an `if (...)` whose body contains the write, and
    `classList.toggle(name, <expr>)` whose second argument IS the condition. Anything else is
    unconditional, which is itself the finding.
    """
    line_start = src.rfind("\n", 0, pos) + 1
    stmt_start = max(src.rfind(";", 0, pos), src.rfind("{", 0, pos), line_start - 1) + 1
    stmt = src[stmt_start:src.find(";", pos) + 1 if src.find(";", pos) > 0 else pos]

    m = re.search(r"\bif\s*\(", stmt)
    if m:
        i, depth = m.end(), 1
        while i < len(stmt) and depth:
            if stmt[i] == "(":
                depth += 1
            elif stmt[i] == ")":
                depth -= 1
            i += 1
        return stmt[m.end():i - 1]

    t = re.search(r"classList\s*\.\s*toggle\s*\(\s*['\"]engine-driven['\"]\s*,", stmt)
    if t:
        i, depth = t.end(), 1
        while i < len(stmt) and depth:
            if stmt[i] == "(":
                depth += 1
            elif stmt[i] == ")":
                depth -= 1
            i += 1
        return stmt[t.end():i - 1]
    return None


#: Identifiers never worth following: globals, and names so common that resolving them drags the
#: whole document in. Following them cost 87 seconds against a 120-second gate — a pass that close
#: to its own timeout is a flake waiting for a slower runner.
_NOFOLLOW = frozenset((
    "window", "document", "location", "body", "self", "top", "search", "test", "e", "a", "b", "c",
    "i", "j", "k", "n", "s", "t", "v", "x", "y", "true", "false", "null", "undefined", "var",
    "let", "const", "function", "return", "if", "else", "try", "catch", "typeof", "new", "this",
    "String", "Number", "Boolean", "Object", "Array", "JSON", "Math", "classList", "className",
))


def _strip_js_comments(js):
    """JS with // and /* */ comments and string/regex literals blanked, line count preserved.

    Blanked rather than removed so offsets and line numbers still line up — a guard that reports
    the wrong line sends the next reader to the wrong place.
    """
    out, i, n = [], 0, len(js)
    while i < n:
        c = js[i]
        two = js[i:i + 2]
        if two == "//":
            j = js.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif two == "/*":
            j = js.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in js[i:j])); i = j
        elif c in "\"'`":
            # ⚠ STRINGS ARE SKIPPED OVER, NOT BLANKED. Blanking them removed the very literal the
            # site detector searches for — `classList.add('engine-driven')` became
            # `classList.add()` and the guard reported "no site writes the class", failing on
            # correct code. That is the same mistake as test_safe_copy's positive assertion an
            # hour earlier: a stripper that removes string literals cannot be used by a check that
            # looks FOR a string literal. Comments are the thing that must not answer for code;
            # strings are code. They are still walked past so a `//` inside one is not mistaken
            # for a comment. [[source-reading-guard]]
            j, q = i + 1, c
            while j < n and js[j] != q:
                if js[j] == "\\":
                    j += 1
                if js[j:j + 1] == "\n" and q != "`":
                    break
                j += 1
            j = min(j + 1, n)
            out.append(js[i:j]); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


def _resolve(src, expr, hops=4):
    """Inline what the expression READS: same-file functions it calls, and vars it names.

    ⚠ Only identifiers the CONDITION actually references are followed. That is the whole point:
    a `var _framed = window.top !== window.self` left behind as a dead variable is not read by
    the condition, so it is never inlined, and the guard stays red — which is the regression the
    v2471 review reproduced against the previous version of this check.
    """
    # SEARCH THE SCRIPT BODIES, NOT THE 6 MB DOCUMENT. The class literal only ever appears in JS;
    # scanning the stylesheet and 45k lines of markup for every identifier is what made this slow.
    # ⚠ AND IT MUST BE CODE, NOT PROSE. The resolver was reading raw source, so an inlined value
    # could carry comment text and regex literals with it — a real run pulled in
    # "/* = engine */ 1` IS A CLAIM ABOUT CONTEXT..." from a comment and a `engine=1` from inside
    # a regex literal. It happened to still fail correctly, by the arrangement of that file rather
    # than by design, and the review named the general case: a comment saying
    # `window.top !== window.self` would satisfy the assertion. Comments and string literals are
    # blanked before anything is resolved, so only executable text can answer for the code.
    # [[source-reading-guard]] [[feedback-comments-vs-code]]
    hay = _strip_js_comments("\n".join(src[a:b] for a, b in _script_regions(src)) or src)
    seen, out = set(), expr
    for _ in range(hops):
        grew = False
        if len(seen) >= 40:      # a bounded walk; an unbounded one is how a gate becomes a hang
            break
        for ident in set(re.findall(r"\b([A-Za-z_$][\w$]*)\b", out)):
            if ident in seen or ident in _NOFOLLOW or len(ident) < 2:
                continue
            d = re.search(r"function\s+%s\s*\([^)]*\)\s*\{" % re.escape(ident), hay)
            if d:
                i, depth = d.end(), 1
                while i < len(hay) and depth:
                    if hay[i] == "{":
                        depth += 1
                    elif hay[i] == "}":
                        depth -= 1
                    i += 1
                seen.add(ident)
                out += "\n/* fn %s */ " % ident + hay[d.end():i]
                grew = True
                continue
            # ⚠ EVERY ASSIGNMENT, NOT THE FIRST. The real code declares `var _framed = true;` and
            # then REASSIGNS it inside a try: `_framed = (window.top !== window.self)`. Taking
            # only the declaration resolved the condition to the literal `true` and the guard went
            # red on correct code — its own reach again, one hop further out than last time.
            hits = re.findall(r"\b%s\s*=\s*([^;\n]+)" % re.escape(ident), hay)
            if hits:
                seen.add(ident)
                for h in hits[:8]:
                    out += "\n/* = %s */ " % ident + h
                grew = True
        if not grew:
            break
    return out


class AppCtxNav(unittest.TestCase):

    def test_engine_driven_class_requires_a_real_frame(self):
        """Every site that puts `engine-driven` on the body must be gated on a REAL frame.

        ⚠⚠ THIS TEST WAS DEFEATED TWICE BY THE v2471 REVIEW, BOTH REPRODUCED ON COPIES, AND BOTH
        HOLES ARE THE SAME MISTAKE: it measured its own reach instead of the code.

          1. ITS DETECTOR SAW ONE CALL SHAPE. It matched the literal
             `classList.add('engine-driven')`, so rewriting a site to
             `classList.toggle('engine-driven', <test>)`, to `className += ' engine-driven'`, or
             even to `classList.add('engine-driven','x')` — two arguments defeat the `\\s*\\)`
             tail — made that site INVISIBLE to it. Measured: the module went green with REG-443
             restored and a top-level board back to 0 of 19 tabs.
          2. ITS ASSERTION CHECKED PRESENCE, NOT CONTROL. It asked whether the framing test
             appeared anywhere in the enclosing scope. Leaving `var _framed = window.top !==
             window.self` in place as a DEAD VARIABLE while dropping `&& _framed` from the
             condition — the most ordinary kind of regression — also passed.

        So it now finds every WRITE of the class by any mechanism, and requires the framing test
        inside the CONTROLLING CONDITION of each: resolved transitively through same-file function
        calls AND through local `var x = …` assignments, so a variable only counts when the
        condition actually reads it. [[source-reading-guard]] [[regression-guard]]

        ⚠ A source guard can always be out-refactored. `tests/v2473_engine_driven_nav.spec.ts`
        asserts the same law BEHAVIOURALLY on a rendered page, and that one cannot be.
        """
        # ⚠⚠ STRIP FIRST, THEN EXTRACT — the order was the whole defect. Comments were being
        # blanked inside `_resolve`, but `_controlling_condition` read the RAW source, so
        #     if (engineDriven() /* window.top !== window.self */) ...add('engine-driven')
        # handed the framing phrase to the matcher inside a COMMENT while `framed()` had been
        # deleted from engineDriven(). Reproduced by the review: both write sites ungated, a
        # top-level ?engine=1 board back to 0 of 19 tabs, and this module reporting "Ran 3 tests
        # ... OK". The strip has to happen before anything is read out of the text, not after.
        # [[source-reading-guard]]
        src = _strip_js_comments(_src())
        sites = _class_write_sites(src)
        self.assertTrue(
            sites,
            "no site writes the engine-driven class by any mechanism this guard knows. Either it "
            "was removed — in which case the CSS that reads it is now dead — or it is written a "
            "way this detector cannot see, which is the hole the v2471 review reproduced.")
        for pos, how in sites:
            cond = _controlling_condition(src, pos)
            self.assertIsNotNone(
                cond,
                "a site writes engine-driven (%s) with no controlling condition at all — it is "
                "applied unconditionally, so a top-level board hides its own tab row." % how)
            resolved = _resolve(src, cond)
            self.assertRegex(
                resolved, r"window\.top\s*!==\s*window\.self",
                "a site writes `engine-driven` (%s) whose controlling condition does not test "
                "that the document is framed:\n    %s\nThat class hides the whole tab row on the "
                "theory that the console shell's rail replaces it. Top-level there is no rail, "
                "and the page hides its nav for nothing. (Condition resolved through calls and "
                "local assignments; a dead `_framed` variable the condition never reads does not "
                "count.)" % (how, cond.strip()[:200]))

    def test_the_framing_LAW_holds_when_the_function_is_RUN(self):
        """⚠⚠ NO COMMENT CAN ANSWER THIS ONE, BECAUSE IT EXECUTES THE FUNCTION.

        The sibling test above reads source text, and the v2479 review proved a comment can
        still answer for the law: `_strip_js_comments` treats every ` as a plain string opener
        with no handling of ${} interpolation or regex literals, so on the SHIPPED bible.html it
        swallows 1.29 M chars in bogus 'string' spans and **1,019 of 4,749 script comments
        survive it byte for byte**. Delete `&& framed()` from engineDriven(), leave a comment
        containing `window.top !== window.self` anywhere the resolver reaches, and the module
        reports "Ran 3 tests ... OK" while a top-level ?engine=1 board hides all 19 tabs.

        Perfecting a hand-rolled JS tokenizer is not the fix; not depending on one is. This
        extracts the real functions from the real bible.html and RUNS them under both framing
        states. A comment cannot change what node computes. [[source-reading-guard]]
        """
        import json as _json
        import shutil as _shutil
        import subprocess as _subprocess
        import tempfile as _tempfile

        node = _shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not installed, so the law could not be RUN — that "
                                    "is UNKNOWN, not a pass")

        src = _src()
        bodies = []
        for fn in ("framed", "engineDriven"):
            m = re.search(r"function\s+%s\s*\(" % fn, src)
            self.assertTrue(m, "function %s() is gone from bible.html — has the framing gate "
                               "been renamed or removed?" % fn)
            i = src.index("{", m.end() - 1)
            depth = 0
            for j in range(i, len(src)):
                if src[j] == "{":
                    depth += 1
                elif src[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            bodies.append(src[m.start():j + 1])

        harness = """
        var __FRAMED_STATE = %s, __QS = %s;
        var window = {};  window.self = {};  window.top = __FRAMED_STATE ? {} : window.self;
        var location = { search: __QS };
        function URLSearchParams(q){ this._q = String(q || ""); }
        URLSearchParams.prototype.get = function(k){
          var m = this._q.replace(/^\\?/, "").split("&").filter(function(p){
            return p.split("=")[0] === k; });
          return m.length ? m[0].split("=").slice(1).join("=") : null;
        };
        %s
        console.log(JSON.stringify(engineDriven()));
        """

        def run(is_framed, qs):
            js = harness % ("true" if is_framed else "false", _json.dumps(qs),
                            "\n".join(bodies))
            with _tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                              encoding="utf-8") as fh:
                fh.write(js)
                path = fh.name
            try:
                out = _subprocess.check_output([node, path], stderr=_subprocess.STDOUT,
                                               timeout=60)
                return _json.loads(out.decode("utf-8", "replace").strip())
            finally:
                try:
                    os.unlink(path)
                except Exception:
                    pass

        self.assertIs(
            run(False, "?engine=1"), False,
            "engineDriven() returned TRUE for a document that is NOT framed. That is the v2471 "
            "defect exactly: opening the board top-level with ?engine=1 adds engine-driven and "
            "HIDES ALL 19 TABS — the blank screen he photographed.")
        self.assertIs(
            run(True, "?engine=1"), True,
            "engineDriven() returned FALSE inside a real frame with ?engine=1, so the engine "
            "shell can no longer drive the board at all.")
        self.assertIs(
            run(True, ""), False,
            "engineDriven() returned TRUE with no engine flag — the query parameter is no "
            "longer part of the condition.")

    def test_engine_flag_is_only_ever_written_by_the_iframe(self):
        """The premise of law 1: the shell is the only writer of engine=1."""
        shell = io.open(SHELL, encoding="utf-8").read()
        writers = re.findall(r"engine=1", shell)
        self.assertTrue(writers, "the shell no longer writes engine=1 — re-derive law 1")
        for m in re.finditer(r"engine=1", shell):
            ctx = shell[max(0, m.start() - 400):m.start()]
            self.assertTrue(
                ("tvd-eng" in ctx) or ("iframe" in ctx.lower()) or ("_eng" in ctx),
                "engine=1 is now written somewhere that is not the #tvd-eng iframe:\n  ...%s"
                % ctx[-200:].replace("\n", "\n  "))

    def test_every_app_ctx_tab_is_a_workshop_tab(self):
        """Law 2 — the premise under `body.app-ctx .tabs-data{display:none}`."""
        src = _src()
        # assertTrue, not assertIn — assertIn prints the HAYSTACK, and the haystack here is a
        # 6 MB document. The first red proof of this guard emitted 6.1 MB of bible.html as its
        # failure message, which makes a real failure unreadable.
        self.assertTrue("body.app-ctx .tabs-data{display:none}" in src,
                        "the empty-cluster rule is gone; law 2 no longer guards anything")

        # every tab re-shown by name in app context
        # ⚠ THE FIRST VERSION MATCHED ONE FORMATTING AND MISSED SIX. It required double quotes
        # around the tab name, so `[data-tab='bosses']` — valid CSS, single-quoted — was invisible
        # to it. Reproduced: adding `body.app-ctx .tabs .tab[data-tab='bosses']{display:inline-flex}`
        # left the whole module GREEN while a DATA tab was re-shown by name into a container that
        # `body.app-ctx .tabs-data{display:none}` hides — built, styled, and invisible in the
        # console, which is the exact trap this law exists to catch.
        # Quotes are now optional and either kind, and whitespace is tolerated throughout.
        # ⚠ A regex over CSS will always be approximate. The behavioural half —
        # tests/v2473_engine_driven_nav.spec.ts — asserts this on the RENDERED page, where a
        # formatting cannot hide anything. This is the cheap early warning, not the proof.
        shown = set()
        _TAB = r"body\.app-ctx\s+\.tabs\s+\.tab\[\s*data-tab\s*=\s*['\"]?([^'\"\]]+)['\"]?\s*\]"
        for m in re.finditer(_TAB + r"([^{]*)\{([^}]*)\}", src):
            name, tail, body = m.group(1), m.group(2), m.group(3)
            if re.search(r"display\s*:\s*none", body):
                continue
            if re.search(r"display\s*:\s*(inline-flex|flex|block|inline-block)", body):
                shown.add(name)
            # a selector list: earlier names in the same rule share this body
            for n2 in re.findall(_TAB, tail):
                shown.add(n2)
        self.assertTrue(shown, "no tab is re-shown in app context — the console would be empty")

        # where does each of those buttons actually LIVE in the markup?
        ws = re.search(r'<div class="tabs-workshop"(.*?)</div>\s*</div>', src, re.S)
        self.assertIsNotNone(ws, "could not find the .tabs-workshop container")
        workshop = set(re.findall(r'data-tab="([^"]+)"', ws.group(1)))
        self.assertTrue(workshop, "the workshop container holds no tabs")

        stray = sorted(shown - workshop)
        self.assertEqual(
            stray, [],
            "these tabs are re-shown in app context but do NOT live in .tabs-workshop: %s\n"
            "`body.app-ctx .tabs-data{display:none}` hides the container they sit in, so each one "
            "is built, styled, re-shown by name — and invisible. Either move the tab into the "
            "workshop row or drop that rule and hide the empty clusters individually." % stray)


RED_PROOF = [
    {
        'why': 'REG-443: engineDriven() must AND the ?engine=1 flag with a real frame test — drop `&& framed()` and a top-level board arms `engine-driven`, whose CSS hides the whole tab row, leaving him 0 of 19 tabs.  MEASURED: untampered python3 tv/test_app_ctx_nav.py -> Ran 4 tests in 3.984s / OK; tampered (all 1) python3 tv/test_app_ctx_nav.py -> Ran 4 tests in 3.006s / FAILED (failures=2); reddened law test_app_ctx_nav.AppCtxNav.test_the_framing_LAW_holds_when_the_functio; ALONE python3 -m unittest test_app_ctx_nav.AppCtxNav.test_the_framing_LAW_holds_when_the_function_is_RUN -.',
        'file': 'bible.html',
        'find': '&& framed()',
        'replace': '&& true',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
