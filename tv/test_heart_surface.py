#!/usr/bin/env python3
"""Guards for ♥ THE HEART as a console SURFACE — the route, and the shell it borrows.

tv/test_heart.py guards the derivation. This guards the parts that were actually wrong on the way
in: a panel that reuses another component's shell inherits its LAYOUT as well as its design, and a
route that fails must fail to UNKNOWN rather than to zero.
"""
import ast
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
UI = os.path.join(HERE, "control_ui.html")
APP = os.path.join(HERE, "control_app.py")


class TheCensusRowReaderAnswersEverySHAPE(unittest.TestCase):
    """⚠⚠ v3018 — A MALFORMED ROW MUST BECOME UNKNOWN, NOT AN EXCEPTION.

    `_read_census_row` has one branch whose whole job is "a row that is not the expected shape
    becomes UNKNOWN, which is visible". v3014 added `via` to the two happy returns and left that
    branch returning THREE values while both callers unpack FOUR, so the row that was supposed to
    be safely visible was the one that raised `ValueError: not enough values to unpack`. The
    docstring three lines above it still promised the old arity.

    Found by the post-ship review of v3014 — the arity is invisible to every test that only ever
    feeds WELL-FORMED rows, which is the whole reason the malformed ones are fed here.
    [[unknown-stays-unknown]] [[label-outlived-referent]] [[gate-blind-to-unexercised-input]]"""

    #: shapes a real census could emit if lane_census changed, plus the plainly wrong ones
    SHAPES = ("not-a-dict", {}, {"kind": "LOOP"}, 42, None, [], {"fn": None})

    def test_every_shape_returns_the_same_arity(self):
        import heart
        arities = {}
        for shape in self.SHAPES:
            r = heart._read_census_row(shape)
            arities[repr(shape)[:24]] = len(r)
        self.assertEqual(
            sorted(set(arities.values())), [4],
            "_read_census_row returns different arities for different row shapes (%s) — every "
            "caller unpacks a fixed number, so the odd one out raises ValueError instead of "
            "reporting UNKNOWN" % arities)

    def test_a_malformed_row_reports_UNKNOWN_rather_than_raising(self):
        import heart
        for shape in self.SHAPES:
            try:
                name, kind, watcher, via = heart._read_census_row(shape)
            except Exception as e:
                self.fail("a row of shape %r raised %s: %s — a census row this reader cannot "
                          "parse must become a VISIBLE UNKNOWN, never an exception that takes the "
                          "whole heart down" % (shape, type(e).__name__, e))
            self.assertEqual(kind, "UNKNOWN",
                             "a row of shape %r was classified %r rather than UNKNOWN" % (shape, kind))
            self.assertIsNone(watcher, "a malformed row named a watcher (%r)" % (watcher,))
            self.assertIsNone(via, "a malformed row carried a via (%r)" % (via,))

    def test_a_well_formed_supervised_row_still_carries_via(self):
        """⚠ the other direction — the arity fix must not flatten a real row into UNKNOWN."""
        import heart
        name, kind, watcher, via = heart._read_census_row(
            {"fn": "x", "kind": "LOOP", "supervised": True, "lane": "lane-x", "via": "roster"})
        self.assertEqual((name, kind, watcher, via), ("x", "LOOP", "lane-x", "roster"),
                         "a well-formed supervised row no longer reads back intact")


def _scored_names(organs):
    """Every name an organ row carries a real score for: its own id AND each surface it names. -> set

    ⚠ v3541 — THIS LAW HAD THE PRE-v3093 FORMULA. heart.vessels() keys `scored` by each organ's id and by every
    surface it names (per-surface score, the row's score as the fallback) since v3093; these cases recomputed
    "scorable" from the organ IDS alone. The two agreed only while no surface carried a score. MEASURED
    2026-10-01: the census gained real lane proofs, laneAttacks named those lanes in its surfaces, every watched
    vessel became scorable - correctly - and both cases went red on a true answer. The contract is the one
    heart.py documents beside its loop; this mirrors it so the check stays derived, never typed."""
    out = set()
    for r in organs or []:
        if not isinstance(r, dict):
            continue
        sc = r.get("score")
        sc = sc if isinstance(sc, (int, float)) else None
        if sc is not None:
            out.add(str(r.get("id") or ""))
        per = r.get("surfaceScores") if isinstance(r.get("surfaceScores"), dict) else {}
        for surf in (r.get("surfaces") or []):
            ss = per.get(str(surf or ""), sc)
            if isinstance(ss, (int, float)):
                out.add(str(surf or ""))
    return out


RED_PROOF = [
    {
        #: ⚠ THE v3014 DEFECT, RESTORED EXACTLY. Dropping the fourth value returns this branch to
        #: three while both callers unpack four, so a malformed census row raises instead of
        #: reporting UNKNOWN. Measured before the fix: 'not-a-dict', {} with no "fn", 42 and None
        #: all raised ValueError.
        "why": "returning three values from the malformed-row branch makes the one path whose job "
               "is to render a bad row VISIBLE the path that crashes the heart instead",
        "file": "heart.py",
        "find": '        return str(row)[:40], "UNKNOWN", None, None',
        "replace": '        return str(row)[:40], "UNKNOWN", None',
        "matches": 1,
    },
    {
        "why": 'the law requires this text in control_ui.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'control_ui.html',
        "find": 'window._heartRender',
        "replace": '_HEART2_TAMPERED_',
        "matches": 3,   # measured: window._heartRender occurs 3x in control_ui.html
    },
    {
        "why": "without the in-flight flag a second click during thOpen paints the shelf onto a half-open stage",
        "file": "control_ui.html",
        "find": "TH.shelfOpening || (TH.open && _ov0 && !_ov0.hidden)",
        "replace": "TH.open && _ov0 && !_ov0.hidden",
        "matches": 1,
    },
    {
        "why": "without aborting a cancelled open, thShelf writes the overlay into a shut theatre",
        "file": "control_ui.html",
        "find": "if (!TH.open && !openErr) return",
        "replace": "if (false && !TH.open && !openErr) return",
        "matches": 1,
    },
]

def _block(code, i, cap=20000):
    """From `i` to the END OF ITS OWN BLOCK, by brace depth — a REAL boundary, never a guess.

    ⚠⚠ v2956 — THESE WERE `self.code[i:i + 1600]` AND FRIENDS, AND THE RATCHET CAUGHT THEM.
    `test_a_source_window_must_reach_its_subject` went RED on CI at 48 fixed windows against a
    ceiling of 44, and its message is the whole reason: *"Each one measures a GUESS about how far
    the subject reaches, and the subject grows every time somebody documents it — that is how the
    /api/river guard came to examine nothing."* A window that stops short reports its subject as
    ABSENT, which is a green that lies with the sign flipped.

    ⚠ The `cap` end is a NAME (`stop`), not `i + N`, so this is not the defect wearing a helper:
    the detector flags a slice only when BOTH ends name the same variable.
    [[source-reading-guard]]
    """
    j = code.find("{", i)
    if j < 0:
        return code[i:]                      # no block to walk — over-inclusive, never short
    depth, k, stop = 0, j, min(len(code), i + cap)
    while k < stop:
        c = code[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return code[i:k + 1]
        k += 1
    return code[i:stop]


class TestABorrowedShellBringsItsLayout(unittest.TestCase):
    """★ THE ONE THAT ACTUALLY BIT, TWICE IN THIS FILE'S HISTORY.

    `.fx-body` is a two-column grid belonging to the fleet window. #ver-xref reused .fleet-xref /
    .fxr-win to BE the cross-reference window rather than a lookalike, inherited the grid, and had
    to override it — and wrote a warning saying so. v2443 added #heart-ov the same way, three lines
    under that warning, and inherited the same bug: measured at 1440 the diagram was squeezed to its
    640px min-width, THE VALVES were stranded in a right-hand column, and a horizontal scrollbar
    ran under the whole panel.

    So this pins the LAW, not the two panels that exist today: ANY element reusing the fleet shell
    must carry the override. A test naming #heart-ov would go stale the next time someone reuses
    .fleet-xref — which is exactly how this defect arrived the second time.
    [[regression-guard]] [[d2r-css-last-rule-wins]]
    """

    def setUp(self):
        self.src = io.open(UI, encoding="utf-8").read()

    def test_every_panel_reusing_the_fleet_shell_overrides_the_two_column_grid(self):
        borrowers = set(re.findall(r'<div\s+id="([a-z0-9\-]+)"[^>]*class="[^"]*\bfleet-xref\b', self.src))
        # ⚠ THE OWNER IS NOT A BORROWER, and this guard found that on its very first run. The panel
        # whose id IS the shell's class name is the fleet window itself — it AUTHORED the two-column
        # grid and genuinely uses the second column (.fx-drill, 8 uses). Requiring it to override
        # its own layout would be requiring it to break. Discriminating on `id == class` rather than
        # on a hardcoded name keeps this a law: a third borrower is still caught, and if the fleet
        # window is ever renamed the rule follows it instead of going stale. [[regression-guard]]
        borrowers.discard("fleet-xref")
        self.assertTrue(borrowers, "no panel reuses .fleet-xref any more — if that is deliberate "
                                   "this guard is measuring nothing and should be retired, not "
                                   "left to pass vacuously")
        # collect every selector that sets `display: block` on a .fx-body
        overridden = set()
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", self.src):
            if "display" not in body or "block" not in body:
                continue
            if not re.search(r"display\s*:\s*block", body):
                continue
            for part in sel.split(","):
                m = re.search(r"#([a-z0-9\-]+)\s+\.fx-body\s*$", part.strip())
                if m:
                    overridden.add(m.group(1))
                # ⚠⚠ AND THE CLASS FORM, which is how this is actually written now. v3033 replaced
                # the per-id list with ONE rule — `.fleet-xref .fx-body { display: block }` at
                # control_ui.html:5709 — that covers every borrower at once and cannot be
                # forgotten when a new panel borrows the shell. That is strictly STRONGER than
                # naming ids, and this law could only see ids, so it reported heart-ov and
                # ver-xref as un-overridden while their grid was in fact overridden. Measured:
                # 3 borrowers, 0 per-id rules, 1 class rule. The law was pinning the old spelling
                # of a fix rather than the fix. [[label-outlived-referent]]
                if re.search(r"\.fleet-xref\s+\.fx-body\s*$", part.strip()):
                    overridden |= borrowers
        missing = sorted(b for b in borrowers if b not in overridden)
        self.assertEqual(missing, [],
                         "%s reuse(s) the fleet shell without overriding `.fx-body`'s two-column "
                         "grid. Borrowing a component's shell buys its design AND its layout; the "
                         "content will be laid out as grid items side by side, with the later "
                         "sections stranded in a narrow right column." % ", ".join(missing))

    def test_the_heart_carries_a_render_seam_so_the_animation_can_be_proven(self):
        """His console has 0 FLOWING vessels, so the blood animation cannot run on real data. If
        the seam goes, the only way anyone has ever seen it work goes with it."""
        self.assertIn("window._heartRender", self.src,
                      "the render seam is gone. Without it the flow animation, the heartbeat and "
                      "an OPEN padlock can never be rendered on this machine, and an animation "
                      "nobody has seen run is a claim nobody has checked")

    def test_the_widget_sits_in_the_footer_beside_the_version(self):
        """His words: 'a widget HEART on the bottom of the console next to the version... thats
        where it should be located'. A chip that drifts out of the footer is not that."""
        m = re.search(r"<footer>(.*?)</footer>", self.src, re.S)
        self.assertIsNotNone(m, "the footer markup could not be found — this guard cannot answer, "
                                "which is not the same as passing")
        foot = m.group(1)
        self.assertIn('id="heart-chip"', foot, "the heart widget is not in the footer")
        self.assertLess(foot.index('id="foot-ver"'), foot.index('id="heart-chip"'),
                        "the heart widget moved AHEAD of the version stamp; he asked for it "
                        "next to the version, after it")


class TestAStampMustSurviveARepaint(unittest.TestCase):
    """★ v2445 — THE DEFECT A COLD CROSS-FAMILY LOOK NAMED AND MY OWN PROBE HAD ALREADY MEASURED.

    v2443 moved the mini-auto padlock INSIDE <b id="miniauto-lbl"> so it would sit inline with the
    words rather than stretching to 147px on its own row. That element is rewritten by
    `_miniPaint` with `lbl.textContent = ...` on EVERY POLL — so the stamp existed for a fraction
    of a second at page load and was then destroyed for ever. On his console the padlock was simply
    ABSENT, on the surface whose entire purpose is making the lock KNOWN.

    The probe had said so: it found THREE .lockchip elements where the markup declares four. I read
    past a count that disagreed with the source. [[feedback-suspect-the-instrument]]

    The law: NO ELEMENT THAT CONTAINS A STAMP MAY BE THE TARGET OF A textContent WRITE. Pinned as a
    rule rather than as "#miniauto-lbl specifically", because the next stamp will be put somewhere
    else by someone who has not read this.
    """

    def setUp(self):
        self.src = io.open(UI, encoding="utf-8").read()
        # ⚠ JUDGE CODE, NOT PROSE. The first run of this guard failed on its OWN comment — the note
        # three lines above `_miniPaint` quotes `lbl.textContent = ...` while explaining the defect,
        # and the regex found it and called it live code. The markup scan needs the HTML comments
        # kept out too, or a commented-out stamp counts as a real one.
        # [[source-reading-guard]] [[feedback-comments-vs-code]]
        self.code = self._strip_comments(self.src)

    @staticmethod
    def _strip_comments(src):
        out, i, n = [], 0, len(src)
        while i < n:
            if src.startswith("<!--", i):
                j = src.find("-->", i)
                i = n if j < 0 else j + 3
            elif src.startswith("/*", i):
                j = src.find("*/", i)
                i = n if j < 0 else j + 2
            elif src.startswith("//", i) and not src.startswith("://", i - 1):
                j = src.find("\n", i)
                i = n if j < 0 else j
            else:
                out.append(src[i])
                i += 1
        return "".join(out)

    def _wrappers(self):
        """Every id whose element CONTAINS a .lockchip. -> list of (ancestor_id, chip_id)

        ⚠ A REAL PARSER, because the hand-rolled version was wrong and said so loudly. Walking
        backwards for "the nearest opening tag with an id, whose closing tag has not appeared yet"
        named ONE element (#ch-search) as the parent of all four chips — a `</span>` counting error
        across 6 MB of nested markup. A guard that misidentifies its own subject reports confident
        nonsense, and would have sent the next reader to rewrite an unrelated element.
        """
        from html.parser import HTMLParser

        class _P(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self, convert_charrefs=True)
                self.stack, self.found = [], []

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                if "lockchip" in (a.get("class") or "").split() or \
                   re.search(r"\blockchip\b", a.get("class") or ""):
                    chip = a.get("id") or "?"
                    for _t, eid in self.stack:
                        if eid:
                            self.found.append((eid, chip))
                if tag not in ("br", "img", "input", "hr", "meta", "link", "source"):
                    self.stack.append((tag, a.get("id")))

            def handle_endtag(self, tag):
                for idx in range(len(self.stack) - 1, -1, -1):
                    if self.stack[idx][0] == tag:
                        del self.stack[idx:]
                        return

        p = _P()
        p.feed(self.code)
        return sorted(set(p.found))

    def test_no_element_holding_a_stamp_is_rewritten_by_textContent(self):
        wrappers = self._wrappers()
        # PRINT THE MATCH COUNT — a guard that silently matched nothing is a guard that passes for
        # the wrong reason, and this repo has paid for that four times. [[regression-guard]]
        self.assertTrue(wrappers,
                        "this guard found ZERO stamp wrappers, so it is measuring nothing. Either "
                        "every .lockchip was removed or the markup shape changed under the regex")
        bad = []
        for eid, chip in wrappers:
            # `$('id').textContent =` , and `var x = $('id')` followed by `x.textContent =`
            if re.search(r"\$\(\s*['\"]%s['\"]\s*\)\s*\.textContent\s*=" % re.escape(eid), self.code):
                bad.append("%s (holds %s) is written directly" % (eid, chip))
                continue
            for vm in re.finditer(r"var\s+(\w+)\s*=\s*\$\(\s*['\"]%s['\"]\s*\)" % re.escape(eid),
                                  self.code):
                var = vm.group(1)
                # ⚠ SCOPED TO THE FUNCTION BODY, NOT THE WHOLE FILE. `lbl` is an ordinary variable
                # name used in several unrelated handlers here; a file-wide search for
                # `lbl.textContent =` would convict this element of somebody else's write. The
                # window is a heuristic (a function body, not a parsed scope) and it is stated as
                # one — it can still miss a write further down its own function. It cannot invent
                # one belonging to a different function, which is the direction that matters.
                # And it reads self.code: the first two runs of this guard failed on its OWN
                # comment, which quotes `lbl.textContent = ...` while explaining the defect.
                window = self.code[vm.end():vm.end() + 3000]
                if re.search(r"\b%s\s*\.textContent\s*=" % re.escape(var), window):
                    bad.append("%s (holds %s) is written via `%s.textContent =`" % (eid, chip, var))
                    break
        self.assertEqual(bad, [],
                         "a stamp lives inside an element that gets rewritten, so it is destroyed "
                         "on the first repaint and the lock silently stops being shown: %s. Give "
                         "the element a text node of its own and write THAT."
                         % "; ".join(bad))


class TestADoorMayNotFailInSilence(unittest.TestCase):
    """★ v2446 — HE FOUND THIS ONE ON HIS OWN SCREEN, and the console had nothing to say about it.

    "now the theatre mode/shelf mode is swallowed i cant see it rendering when i click on it...
    but its like swallowed." Then: "hook that to the heart of the console so it doesnt regress in
    the future either."

    THE DEFECT: the Shelf handler was `if (!TH.open) { await thOpen(); }` with no catch, followed by
    `try { thShelf(true); } catch(e){}`. A REJECTED thOpen() throws straight out of the async
    handler, so thShelf never runs — the stage is left open and empty and NOTHING anywhere says so.
    He photographed a black rectangle.

    ⚠ AND THE CHANNEL TO SAY IT ALREADY EXISTED. ui_fault_record's own docstring reads: "THE
    CONSOLE HAD NO WAY TO SAY IT WAS BROKEN. He found the black-screen stage himself, twice, and
    reported it with screenshots; nothing in the tree knew." That was v2228. This is the third
    time, on the same surface, through a door nobody wired to it.
    """

    def setUp(self):
        self.code = TestAStampMustSurviveARepaint._strip_comments(
            io.open(UI, encoding="utf-8").read())

    def test_the_shelf_door_catches_a_refused_stage(self):
        # REG-2700 grew the handler by a shadow check, and a 1400-character window then stopped short of its end and found
        # nothing. Bounded by its own braces now, like the other Shelf-door laws here. [[source-reading-guard]]
        i = self.code.find("_bshelf.onclick = async function")
        self.assertGreater(i, 0, "the Shelf handler could not be found — this guard cannot answer, "
                                 "which is not the same as passing")
        body = _block(self.code, i)
        self.assertIn("await thOpen()", body, "the handler no longer opens the stage — if that is "
                                              "deliberate this guard is measuring nothing")
        # the await must sit inside a try, and the shelf must still be attempted afterwards
        awaits = body.index("await thOpen()")
        before = body[:awaits]
        self.assertRegex(before[-120:], r"try\s*\{",
                         "`await thOpen()` is not inside a try. A rejected stage throws out of the "
                         "handler and thShelf() never runs, leaving an open black stage and total "
                         "silence — which is exactly what he photographed")
        self.assertLess(body.index("thShelf(true)"), len(body),
                        "the shelf is never attempted")
        self.assertIn("_shelfRefused", body,
                      "nothing reports the refusal. A door that fails silently is worse than one "
                      "that is missing: he cannot tell it from a mis-click")

    def test_the_refusal_reaches_the_console_fault_channel(self):
        """[[the-unjoined-end]] — a reporter with no route is plumbing with no tap."""
        m = re.search(r"function _shelfRefused\b(.{0,1800}?)\n  \}", self.code, re.S)
        self.assertIsNotNone(m, "_shelfRefused is gone")
        body = m.group(1)
        self.assertIn("/api/ui_fault", body, "the refusal never reaches the fault channel")
        self.assertIn("kind", body, "the route REJECTS a fault that does not name its kind (400), "
                                    "so a payload without one is a report nobody ever hears")
        # ⚠ AND IT MUST SAY IT SOMEWHERE VISIBLE WHEN THE STAGE IS NOT. v3891 REG-3532 moved
        # #th-shelfov out of #theatre so the overlay itself has a box when the theatre is shut;
        # the toast is the spoken report if anything else still hides it.
        self.assertIn("toast(", body,
                      "the refusal only writes into #th-shelfov. A message that is only visible "
                      "when the thing works is not an error message")

    def test_the_refusal_handler_is_reachable_so_it_can_be_PROVEN(self):
        """It had never run. Two attempts to reach it failed as instrument errors — overriding
        thOpen only proved the shelf still renders, and overriding thShelf from outside never took
        because it is a closure binding. A refusal handler nobody has watched refuse is a guess."""
        self.assertIn("window._shelfRefused", self.code,
                      "the seam is gone, and with it the only way anything has ever executed this "
                      "handler")

    def test_the_close_control_appears_when_there_is_something_to_close(self):
        """v2443 hid #btn-sim so the Shelf could be the single door. Its handler begins
        `if (TH.open) { thClose(); return; }` and its label becomes "Close Theatre" once open — so
        hiding it unconditionally deleted the way OUT, not a duplicate way in. He said so:
        "it use to say close theatre mode after i click theatre mode"."""
        self.assertRegex(self.code, r"\$\('btn-sim'\)\.hidden\s*=\s*!\s*thOpenNow",
                         "#btn-sim is not tied to whether the theatre is open, so either it is "
                         "always visible (two doors, which he asked me to stop) or always hidden "
                         "(no way to close the theatre, which is how this broke)")


class TestATipDoesNotPaintOverWhatYouAreReading(unittest.TestCase):
    """★ v2452 — the transport's tooltip painted across the shelf's reel cards.

    A cold cross-family read named it: "the dark floating box overlaps and partially obscures the
    three Session cards below it", quoting the transport's own tooltip text.

    ⚠ IT IS NOT THE STRIP, AND MY FIRST PROBE PROVED NOTHING. MEASURED at 1440x900: the shelf ends
    at y=700 and .th-strip starts at 708 — an 8px gap, zero cards under it. The probe enumerated
    .th-strip, .th-transport, #th-drawer and #th-lower, reported cardsUnderAStrip: 0, and had
    simply never looked at #itip. A green about the wrong elements is not a green; the PNG settled
    it and the eye was right.

    ⚠ AND THE FIRST FIX PATCHED THE WRONG PATH. #itip is placed two ways — move() follows the
    cursor, anchor() pins to an element — and a `title=` hint goes through say() -> anchor().
    Clamping only move() left the tip at top 671 against a shelf bottom of 700: the clamp existed
    and never ran. Hence this guard is about BOTH paths, not about the behaviour of one.
    """

    def setUp(self):
        self.code = TestAStampMustSurviveARepaint._strip_comments(
            io.open(UI, encoding="utf-8").read())

    def test_both_placement_paths_reach_the_one_clamp(self):
        i = self.code.find("_clampBelowOverlay: function")
        self.assertGreater(i, 0, "the shared clamp is gone")
        for fn in ("move: function(x, y){\n        if (!el) return;", "anchor: function(node){"):
            j = self.code.find(fn)
            self.assertGreater(j, 0, "placement path %r not found — this guard cannot answer, "
                                     "which is not the same as passing" % fn[:20])
            window = _block(self.code, j)
            self.assertIn("_clampBelowOverlay", window,
                          "the %r placement path does not reach the clamp. Patching one path and "
                          "not the other is exactly how the first fix measured as having no effect"
                          % fn[:20])

    def test_the_clamp_only_fires_for_an_OPEN_overlay(self):
        """A tooltip floating above the page is what a tooltip is FOR. This must not fight that —
        it only refuses to cross an open full-height overlay."""
        i = self.code.find("_clampBelowOverlay: function")
        body = _block(self.code, i)
        self.assertIn("ov.hidden", body,
                      "the clamp does not check whether the overlay is open, so it would displace "
                      "every tooltip on the console whether or not the shelf is up")
        self.assertIn("return top", body,
                      "the clamp never returns the position unchanged, so it has no pass-through "
                      "case and always moves the tip")


class TestTheShelfIsNotATrap(unittest.TestCase):
    """★ Konyo: "the shelf is kinda of a trapped area when clicked i cant really get out of it..
    where is the logic of close theatre mode or close the shelf.. something there is meshing up"

    MEASURED, all four ways out, from a real shelf-open state — NOT ONE closed both layers:

        the shelf's own ✕          shelf SHUT        stage STILL OPEN
        the Close Theatre button   shelf STILL OPEN  stage SHUT
        Escape                     shelf SHUT        stage STILL OPEN
        clicking THE SHELF again   nothing at all    nothing at all

    ⚠ AND THIS RETRACTED AN EARLIER DIAGNOSIS. His "black empty panel" was attributed to a
    rejected thOpen() swallowing the shelf. That defect was real, but THIS reproduces every time:
    ✕ or Escape closed the shelf and left him on the bare stage one layer down.

    ⚠ TWO WRONG FIXES BEFORE THE RIGHT ONE, both kept in the comments because the second looked
    more principled than the first and was not:
      1. a TH.shelfIsDoor flag set at the door — wrong for the flow he uses (door -> open a reel ->
         peek at the shelf -> ✕ would have thrown him out of the reel)
      2. "does the stage have a reel loaded" — sounds better, measured worse: opening the theatre
         AUTO-LOADS the last session, so a reel is always loaded even straight through the door.
         Having a reel is not the same as having asked for one.
    The flag is right; it just has to be CLEARED where its meaning changes — thLoadSession, the
    moment he opens a reel.
    """

    def setUp(self):
        self.code = TestAStampMustSurviveARepaint._strip_comments(
            io.open(UI, encoding="utf-8").read())

    def test_closing_the_theatre_does_not_leave_the_shelf_armed(self):
        """thClose's own comment states the rule for a sibling layer: 'never leave the drawer armed
        behind a closed theatre'. The shelf was the one exception."""
        i = self.code.find("function thClose()")
        self.assertGreater(i, 0, "thClose could not be found")
        body = _block(self.code, i)
        self.assertIn("th-shelfov", body,
                      "thClose does not hide the shelf overlay, so Close Theatre leaves it hanging "
                      "over a closed stage")

    def test_the_door_toggles(self):
        i = self.code.find("_bshelf.onclick")
        self.assertGreater(i, 0)
        body = _block(self.code, i)
        self.assertIn("thClose()", body,
                      "clicking THE SHELF while it is open does nothing — the one control he would "
                      "reach for first cannot get him out")

    def test_a_second_click_while_opening_closes(self):
        """thOpen sets TH.open before the overlay exists. Requiring the overlay visible made a
        second click during that wait fall through and paint the shelf onto a half-open stage."""
        i = self.code.find("_bshelf.onclick")
        self.assertGreater(i, 0)
        body = _block(self.code, i)
        self.assertIn("TH.shelfOpening", body,
                      "the door does not mark an in-flight open, so a second click cannot tell "
                      "cancel-this-open from open-the-shelf-on-a-reel")
        self.assertIn("TH.shelfOpening || (TH.open && _ov0 && !_ov0.hidden)", body,
                      "the close predicate still requires the overlay visible, which is the "
                      "in-and-out trap: TH.open is true and the overlay is not")

    def test_a_cancelled_open_does_not_paint_the_overlay(self):
        """After await thOpen, a cancelled attempt has TH.open false. Painting thShelf(true)
        anyway writes the overlay into a display:none theatre — hidden=false, height 0."""
        i = self.code.find("_bshelf.onclick")
        self.assertGreater(i, 0)
        body = _block(self.code, i)
        self.assertIn("if (!TH.open && !openErr) return", body,
                      "a cancelled door-open still calls thShelf(true), so the overlay arms "
                      "inside a shut theatre")

    def test_both_quiet_exits_consult_the_door(self):
        """✕ and Escape must both ask whether the shelf WAS the door. One without the other is the
        half-fix that made Escape keep failing after ✕ was fixed."""
        # ⚠ ANCHOR ON THE HANDLER, NOT THE NAME. The first version searched for "th-shelf-x" and
        # found the CSS rule `#th-shelf-x:focus-visible` six thousand lines above the handler, then
        # judged the wrong window. Grepping a bare id finds whichever occurrence comes first, and
        # the first one is almost never the code. [[source-reading-guard]]
        for marker, what in (('closest(\'#th-shelf-x\')', "the shelf's x"),
                             ("function thEscUnwind", "Escape")):
            i = self.code.find(marker)
            self.assertGreater(i, 0, "%s handler not found — this guard cannot answer, which is "
                                     "not the same as passing" % what)
            self.assertIn("_thShelfWasTheDoor", self.code[max(0, i - 400):i + 700],
                          "%s does not consult the door flag, so it drops him onto a bare stage"
                          % what)

    def test_the_flag_is_cleared_where_its_meaning_changes(self):
        """Set at the door, cleared when a reel is opened. Without the clear, ✕ throws him out of
        a reel he chose — the over-fix. thLoadSession is the single path into a reel
        (_dossierToTheatre calls it), so clearing there covers every route in."""
        i = self.code.find("async function thLoadSession")
        self.assertGreater(i, 0, "thLoadSession not found")
        self.assertIn("shelfIsDoor = false", _block(self.code, i),
                      "the door flag is never cleared when a reel opens, so ✕ would close the "
                      "whole theatre out from under a reel he chose to watch")

    def test_the_way_out_appears_with_the_stage_not_on_the_next_poll(self):
        i = self.code.find("function thLit()")
        self.assertGreater(i, 0)
        self.assertIn("sim.hidden = !TH.open", _block(self.code, i),
                      "btn-sim's visibility is set only by the status poll, so after opening the "
                      "theatre the Close control stays hidden until the next tick — measured as "
                      "HIDDEN/ABSENT by a probe clicking it right after opening")


class TestEveryLockNamesItself(unittest.TestCase):
    """★ v2450 — THREE ROWS ALL SAID "VAULT", and a cold cross-family read of the panel found it:
    "several rows are identical (three VAULT entries) with no visible differentiation."

    It is the defect Konyo had already named once — "i want to know which specifically is still
    locked and waiting to self prove itself" — and I fixed only half of it. The DIAGRAM got the
    specific lock id; the LIST kept rendering `surface || lock`, and three of the five locks share
    the surface VAULT. Half a fix reads as a whole one until someone counts.

    The law: the label a lock renders under must be UNIQUE among the locks, because a lock you
    cannot tell from its neighbour cannot be acted on. [[sweep-dont-ask]]
    """

    def test_the_list_label_leads_with_the_unique_part(self):
        code = TestAStampMustSurviveARepaint._strip_comments(
            io.open(UI, encoding="utf-8").read())
        self.assertNotIn("_hrtEsc(L.surface || L.lock)", code,
                         "a lock row is labelled by SURFACE first. Three locks share the surface "
                         "VAULT, so the list prints VAULT three times with only the bar numbers to "
                         "tell them apart")

    def test_the_declared_locks_have_unique_ids_but_NOT_unique_surfaces(self):
        """The reason this defect exists at all, pinned so nobody 'simplifies' the label back:
        surfaces are deliberately shared and ids are not."""
        import self_arming as SA
        ids = sorted(SA.LOCKS)
        surfaces = [SA.LOCKS[k]["surface"] for k in ids]
        self.assertEqual(len(set(ids)), len(ids), "two locks share an id")
        self.assertLess(len(set(surfaces)), len(surfaces),
                        "every lock now has a unique surface, so this guard is measuring nothing "
                        "and the label could safely be the surface again — check before deleting "
                        "it, but do not leave it passing vacuously")


class TestAMeasurementNobodyReadsIsNoMeasurement(unittest.TestCase):
    """★ CF-13. The auditor was RIGHT and read by NOBODY.

    auto_scope.undeclared_reach_abilities computes which lanes forbid an ability their reach can
    still perform. It is correct, it is deliberately non-failing, and its author wrote the rule
    into the docstring: "DO NOT PROMOTE THIS TO A FAILING GATE... a gate that fails on all four
    teaches him to skip the row — the exact defect CF-10 records three instances of."

    The defect CF-13 names was never the function. It was that its ONLY CALLERS REPO-WIDE WERE ITS
    OWN TESTS. A measurement computed correctly and read by nobody is identical, from every surface
    he looks at, to one never taken. [[the-unjoined-end]] [[plumbing-with-no-tap]]
    """

    def test_the_auditor_has_a_PRODUCTION_caller_not_only_tests(self):
        import glob
        callers = []
        for p in glob.glob(os.path.join(HERE, "*.py")):
            name = os.path.basename(p)
            if name.startswith("test_") or name == "auto_scope.py":
                continue
            if "undeclared_reach_abilities" in io.open(p, encoding="utf-8").read():
                callers.append(name)
        self.assertTrue(callers,
                        "undeclared_reach_abilities has no caller outside its own tests. It is "
                        "computed correctly and read by nobody, which from every surface he looks "
                        "at is the same as never having been measured")

    def test_it_reaches_the_heart_payload(self):
        src = io.open(APP, encoding="utf-8").read()
        self.assertIn('"reach": scope_reach_state()', src,
                      "the scope rows never reach /api/heart, so nothing renders them")

    def test_it_REPORTS_and_never_REFUSES(self):
        """Its author's ruling, kept enforceable: this may inform, never fail a build. If it ever
        starts refusing, three rows of reach-noise begin failing pushes and he learns to skip the
        row — which is the exact outcome the ruling exists to prevent."""
        import control_app as C
        rep = C.scope_reach_state()
        self.assertIn("ok", rep)
        # ⚠ THE FIRST VERSION OF THIS ASSERTION FAILED ON ITS OWN PROSE — it searched the summary
        # for the word "fail", and the summary explains WHY it must not fail ("a gate failing on
        # all of them would teach you to skip the row"). Judging a behaviour by looking for a word
        # is the same mistake as grepping source and hitting your own comment. The behaviour is
        # what matters: it must not be registered as a GATE, because a gate is the one thing that
        # can turn this into a refusal. [[source-reading-guard]] [[feedback-comments-vs-code]]
        # ⚠⚠ THE REGISTRY, NOT THE SOURCE TEXT — and the previous cut of this line was one prose
        # blurb away from lying. It ran `assertNotIn("scope_reach", <run_gates.py source>)`, so
        # writing the words "scope reach" into any `why=` explanation in that file would have
        # turned this guard red while nothing was registered, and deleting the check would have
        # been the obvious fix. It is the same defect the comment above already names one level
        # up, and it survived because the comment describes it instead of the code avoiding it.
        # Today `scope_reach` occurs ZERO times in run_gates.py, so this was latent rather than
        # lying — a guard that has not been caught out yet. Ask the LIST OF GATES.
        # [[source-reading-guard]]
        # ⚠⚠⚠ AND THE REGISTRY FORM WAS UNSATISFIABLE — v2658. It asserted that no gate named
        # `*scope_reach*` is registered, while `test_control.TestNoOrphanSuite` REQUIRES every
        # `tv/test_*.py` to be registered. The moment `tv/test_scope_reach_signal.py` existed
        # (v2649) one rule compelled what the other forbade; CI went red and no edit to either
        # side could satisfy both. THE CONTRADICTION WAS THE FINDING.
        #
        # Registration was only ever a PROXY for the author's ruling — *this may inform, never
        # fail a build.* The proxy became unsatisfiable, so this asks the property it stood for:
        # no case in that suite may assert an exact value of the LIVE reading, because `reach`
        # walks control_app's own call graph and therefore tracks THIS MODULE'S GROWTH. Fixtured
        # cases keep their hard assertions — they are deterministic on every venue.
        #
        # ⚠ ONE ROUTINE, TWO CALLERS. The check is IMPORTED from the suite it is about rather
        # than re-implemented here. A safety routine that exists twice is [[copy-drift]] §7, and
        # a law that lands in one copy is not a law — which is exactly how the old form drifted
        # into forbidding its own file's existence.
        import run_gates as _rg
        names = [str(getattr(g, "name", "")) for g in getattr(_rg, "GATES", [])]
        self.assertTrue(names, "run_gates declares no gates at all — this guard is measuring "
                               "nothing, which is not the same as measuring a clean registry")
        import test_scope_reach_signal as _srs
        offenders = _srs.live_signal_assertions()
        self.assertEqual(
            offenders, [],
            "%s assert an exact value of the LIVE scope-reach reading, so a push would start "
            "failing the day `control_app.py` grows past the last narrow row (headroom: 3). The "
            "author's ruling is that this aid may inform and never refuse." % (offenders,))
        # REG-1893 - `.get("rows") or []` reads a renamed or missing key as no rows, and no rows lack a reach
        self.assertTrue(rep.get("rows"), "scope_reach_state() carried no rows, so 'every row carries its reach' "
                                         "is vacuous: %r" % sorted(rep))
        for row in (rep.get("rows") or []):
            self.assertIn("reach", row,
                          "a row without its reach count hides the noise that makes it unreadable "
                          "— the count is the only thing that tells a signal from an artefact here")

    def test_a_broken_auditor_is_UNKNOWN_never_an_empty_all_clear(self):
        import control_app as C, auto_scope as A
        real = A.undeclared_reach_abilities
        A.undeclared_reach_abilities = lambda m: (_ for _ in ()).throw(RuntimeError("boom"))
        self.addCleanup(setattr, A, "undeclared_reach_abilities", real)
        rep = C.scope_reach_state()
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["rows"], [])
        self.assertIn("boom", rep["why"],
                      "the failure was swallowed — an auditor that cannot run must not render as "
                      "a lane list of length zero, which reads as 'nothing to see'")


class TestTheRouteFailsToUnknownNeverToZero(unittest.TestCase):
    """[[unknown-stays-unknown]] — 'nothing runs unwatched' and 'nobody could look' are opposite
    facts, and a heart that renders empty on a broken census claims the safe one."""

    def setUp(self):
        import control_app as C
        self.C = C

    def test_an_unreadable_census_returns_ok_False_with_NO_counts(self):
        import heart as H
        real = H.vessels
        H.vessels = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        self.addCleanup(setattr, H, "vessels", real)
        self.C._HEART_MEMO["v"] = None          # a memo hit would hide the failure entirely
        self.addCleanup(self.C._HEART_MEMO.update, {"t": 0.0, "v": None})
        rep = self.C.heart_state(force=True)
        self.assertFalse(rep["ok"])
        self.assertIsNone(rep["counts"],
                          "a census that could not be taken produced COUNTS. An empty heart and an "
                          "unreadable one look identical on screen and only one of them is safe")
        self.assertIn("boom", rep["why"], "the failure was swallowed — a reason nobody can read is "
                                          "indistinguishable from no failure")

    def test_the_route_is_dispatched_and_calls_heart_state(self):
        """[[the-unjoined-end]] — this repo's most repeated defect is two halves built right and
        never joined. A heart_state() nothing routes to is exactly that."""
        tree = ast.parse(io.open(APP, encoding="utf-8").read())
        found = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for c in node.comparators:
                if isinstance(c, ast.Constant) and c.value == "/api/heart":
                    found = True
        self.assertTrue(found, "/api/heart is not dispatched anywhere in control_app.py")
        self.assertIn("heart_state(force=", io.open(APP, encoding="utf-8").read(),
                      "the route exists but does not reach heart_state()")

    def test_the_memo_is_a_cache_of_a_DERIVATION_and_it_expires(self):
        """A stored picture drifts from the territory; a 45s memo of a derivation does not. If the
        TTL ever became effectively infinite the heart would quietly become a stored diagram."""
        self.assertGreater(self.C._HEART_TTL, 0)
        self.assertLessEqual(self.C._HEART_TTL, 120,
                             "the heart's memo outlives two minutes. It is a cache of a "
                             "derivation, not a stored diagram, and the difference is the TTL")


class TestRosterRoutesJoinTheHeart(unittest.TestCase):
    """The gate was registered in v2457; the join into heart_state() was not. A mention of
    roster_routes in a comment is not the call. [[the-unjoined-end]] [[source-reading-guard]]"""

    def test_heart_state_calls_roster_route_state(self):
        raw = io.open(APP, encoding="utf-8").read()
        code = "\n".join(l.split("#", 1)[0] for l in raw.split("\n"))
        self.assertEqual(code.count('"rosters": roster_route_state()'), 1,
                         "the roster routes are not joined to the heart, or the join is "
                         "satisfied by a comment")
        self.assertIn("def roster_route_state():", code)


class AVesselMayNotBeToldWorkIsOwedThatCannotLand(unittest.TestCase):
    """⚠⚠ FLOWING WAS UNREACHABLE, AND THE PANEL CALLED IT WORK OWED.

    A vessel turns FLOWING when `scored.get(watcher)` yields a number above zero. `scored` is keyed
    on the ORGAN rows' own ids — lanes, readers, selfArming, board_join — and `watcher` is a LANE
    name, tvd-eagle-watch and its siblings. The two vocabularies are DISJOINT, so the lookup misses
    for every vessel that exists.

    MEASURED, end to end: give every organ a perfect score and the census still reads FLOWING 0;
    give the WATCHER names the same score and 11 turn FLOWING at once. So the branch is dead with
    real data, and under it the panel said "nothing has ever tried to break the watcher — that is
    work owed, not a fault". That is the expensive kind of false: it names a job which, done
    perfectly, would change nothing on the screen.

    This asserts the LAW, not the wiring: a row may only say work is owed when a score for that
    watcher could actually be recorded. It stays green when someone later builds a lane scorer —
    that is the point. [[unknown-stays-unknown]] [[the-unjoined-end]]
    """

    def _heart(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import heart
        return heart

    def test_work_owed_is_only_said_when_a_score_could_land(self):
        """REG-1953 - DRIVEN OVER TWO FIXTURE ORGAN WORLDS, NEVER THE TREE'S OWN. This read the live census
        (HE.report over this tree's proof records) and its REG-1893 vacuity guard demanded a WATCHED vessel - so in
        his main checkout, where the lanes carry real scores (FLOWING 22, WATCHED 0: the world this docstring calls
        the point), it went red untampered and refused the v3602 push after 80 minutes, while every worktree (no
        proof records) passed. Judged in each world the way the census means it - once ANY watcher can be scored,
        an unscored one is work that could land:
          world A - no organ carries a score: every WATCHED row says it is a missing scorer, never work owed;
          world B - one organ scores one watcher at 0: every WATCHED row says the work is owed."""
        import unittest.mock as _mock
        H = self._heart()
        with _mock.patch.object(H, "_health_rows", lambda: ([], "")):
            rep_a = H.vessels()
        watched_a = [v for v in (rep_a.get("vessels") or []) if v.get("state") == "WATCHED"]
        # REG-1893 - a census that refused (or a renamed key) leaves no WATCHED vessel, and the law asks nothing
        self.assertTrue(watched_a, "with no organ scores the census returned no WATCHED vessel, so no row's "
                                   "'work owed' was judged: %r" % (rep_a.get("counts"),))
        w = watched_a[0].get("watcher")
        organs_b = [{"id": "fixture-scorer", "score": 0.0, "surfaces": [w]}]
        with _mock.patch.object(H, "_health_rows", lambda: (list(organs_b), "")):
            rep_b = H.vessels()
        for world, rep, organs in (("A", rep_a, []), ("B", rep_b, organs_b)):
            watchers = {v.get("watcher") for v in (rep.get("vessels") or []) if v.get("watcher")}
            scorable = bool(_scored_names(organs) & watchers)
            self.assertEqual(scorable, world == "B", "world %s is not the world this case means" % world)
            judged = 0
            for v in (rep.get("vessels") or []):
                if v.get("state") != "WATCHED":
                    continue
                judged += 1
                why = str(v.get("why") or "")
                # ⚠ MATCH THE CLAIM, NOT A SUBSTRING OF IT. The first version asserted `"work owed"
                # not in why` and went red on the CORRECT sentence, because that sentence ends
                # "...a missing scorer, not work owed by anyone" — the phrase appears inside its own
                # negation. A guard that cannot tell an assertion from its denial is measuring the
                # letters, not the claim.
                if scorable:
                    self.assertIn("work owed, not a fault", why,
                                  "world %s: %s can be scored but the row does not say the work is owed"
                                  % (world, v.get("name")))
                else:
                    self.assertNotIn(
                        "work owed, not a fault", why,
                        "world %s: %s is told sabotage is owed, but no organ publishes a score under its "
                        "watcher's name, so that work could not land however well it was done. "
                        "Nobody-tested-it and nothing-can-record-a-test are different facts."
                        % (world, v.get("name")))
                    self.assertIn("scorer", why,
                                  "world %s: %s does not say WHY it cannot be proven" % (world, v.get("name")))
            self.assertTrue(judged, "world %s judged no WATCHED row" % world)
        self.assertIn("work owed, not a fault",
                      str(([v for v in rep_b["vessels"] if v.get("watcher") == w] or [{}])[0].get("why") or ""),
                      "baseline: world B's scorable watcher does not say work owed - the case cannot tell the worlds apart")

    def test_the_census_never_reports_a_state_it_cannot_reach(self):
        """If FLOWING is unreachable, the panel must not imply otherwise by silence."""
        H = self._heart()
        rep = H.vessels()
        counts = rep.get("counts") or {}
        watched = [v for v in (rep.get("vessels") or []) if v.get("state") == "WATCHED"]
        if not watched:
            raise unittest.SkipTest("no WATCHED vessels to judge")
        for v in watched:
            self.assertIn("scorable", v,
                          "%s does not publish whether a score could ever land for it, so a "
                          "reader cannot tell an unearned state from an unreachable one"
                          % v.get("name"))
        # and the flag must agree with the arithmetic, not be typed in
        organs, _ = H._health_rows()
        # ⚠ v3541 — EVERY vessel's watcher, as vessels() counts them, not only the WATCHED ones. `scorable` answers
        # "could a score land here at all" - whether the organ vocabulary reaches the watcher vocabulary - and
        # the moment one watcher is scored it is no longer WATCHED, so a WATCHED-only population drops exactly
        # the evidence that makes the flag true (measured: tvd-version-drift scored 0.2065 and left the set).
        names = {v.get("watcher") for v in (rep.get("vessels") or []) if v.get("watcher")}
        self.assertEqual(
            watched[0].get("scorable"), bool(_scored_names(organs) & names),
            "the scorable flag disagrees with whether any watcher name appears among the organ "
            "ids — it is being asserted rather than derived")
        if watched[0].get("scorable"):
            self.assertIsInstance(counts.get("FLOWING"), int)
        else:
            # v3044 — FLOWING is UNMEASURED when nothing can score a watcher: None plus a
            # published reason, never a 0 nobody earned. [[zero-needs-a-denominator]]
            self.assertIsNone(counts.get("FLOWING"),
                              "no watcher can be scored, yet FLOWING prints a number it "
                              "could not have measured")
            self.assertTrue(rep.get("flowingWhy"),
                            "FLOWING is None but the census publishes no reason why")



class TheConsoleCanSeeHARDENED(unittest.TestCase):
    """v2569 — the HARDENED tier existed in ONE module and had ZERO consumers.

    ⚠⚠ WHY THIS SUITE EXISTS, MEASURED. `self_arming` has carried HARDENED since v2487 (wilson
    >= 0.900 AND confluence >= 2.50 — three genuinely INDEPENDENT kinds). Grepping tv/ for the
    string found it in `self_arming.py` and a jsonl, and nowhere else: not one surface could
    render it. Every fallback landed on the DANGEROUS side —

        control_app  `open` counted state == "OPEN" only, while self_arming.report() counts
                     OPEN + HARDENED — two tallies of one quantity, disagreeing by construction
        rank map     no `hardened` key, and `?? -1` sorted it BELOW `locked: 0`; the function
                     takes mine[0] after an ascending sort because "the WORST state wins", so
                     the strongest proof state would have dominated its group as the weakest
        _paintChip   anything not open/unproven collapses to `locked` -> a CLOSED PADLOCK
        _HRT_LOCKCOL no key -> `|| '#9aa6b2'`, the SAME grey as UNPROVEN and UNKNOWN

    Konyo's ruling on task 146 is *"YES ARM IT but rmember to do the Wilson score of our own
    style the HARDENING stamp badge on it"*. Locks are BADGED, never enforced — so the badge IS
    the product, and a tier the badge cannot show does not exist to him. Worse than absent: it
    would have shown the most-proven lock in the system as LOCKED, on the console he reads to
    decide whether the deleter is armed.

    These assert BEHAVIOUR (the parsed maps and the tally's output), not the presence of words.
    [[source-reading-guard]]
    """

    @staticmethod
    def _ui():
        with io.open(UI, encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _map(src, decl):
        """Parse one JS object literal into {key: value}. Structure, not prose."""
        i = src.index(decl)
        body = src[i + len(decl):]
        body = body[body.index("{") + 1: body.index("}")]
        out = {}
        for part in body.split(","):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            out[k.strip().strip("'\"")] = v.strip().strip("'\"")
        return out

    def test_hardened_outranks_open_so_it_cannot_dominate_a_group_as_its_worst(self):
        rank = self._map(self._ui(), "var rank =")
        for key in ("locked", "unproven", "open", "hardened"):
            self.assertIn(key, rank,
                          "the rank map has no %r; `?? -1` then sorts it BELOW locked:0 and the "
                          "worst-wins pick would treat it as the weakest state in its group" % key)
        r = {k: int(v) for k, v in rank.items()}
        self.assertGreater(r["hardened"], r["open"],
                           "HARDENED must outrank OPEN — it is strictly stronger evidence, and "
                           "may() already treats the two alike")
        self.assertGreater(r["open"], r["unproven"])
        self.assertGreater(r["unproven"], r["locked"])

    def test_the_padlock_does_not_collapse_hardened_into_locked(self):
        ui = self._ui()
        i = ui.index("state = 'locked';")
        cond = ui[max(0, i - 220):i]
        self.assertIn("'hardened'", cond,
                      "the chip state collapse does not mention 'hardened', so the strongest "
                      "state falls into the `= 'locked'` bucket and paints a CLOSED PADLOCK")

    def test_the_heart_paints_hardened_differently_from_never_tested(self):
        col = self._map(self._ui(), "var _HRT_LOCKCOL =")
        self.assertIn("HARDENED", col,
                      "_HRT_LOCKCOL has no HARDENED key, so `|| '#9aa6b2'` paints the most-proven "
                      "state the same grey as UNPROVEN and UNKNOWN")
        self.assertNotEqual(col["HARDENED"], col.get("UNPROVEN"),
                            "HARDENED and UNPROVEN must not be the same colour — that is "
                            "most-proven and never-tested rendering identically")

    def test_the_river_map_gives_hardened_an_open_padlock(self):
        ui = self._ui()
        # REG-1737 - the map asks the ONE padlock helper now; the HARDENED rule lives in its verdict line
        self.assertIn("      var open = window._lockOpen(L);\n", ui,
                      "the heart's river map decides its padlock by itself again")
        i = ui.index("window._lockOpen = function(l){")
        ret = ui[i:ui.index("\n};", i)]
        self.assertIn("s === 'HARDENED'", ret,
                      "the padlock helper tests only for 'OPEN', so a HARDENED lock draws a "
                      "CLOSED padlock")

    def test_the_server_tally_counts_hardened_as_open_and_reports_it_separately(self):
        """BEHAVIOURAL: feed a HARDENED lock through the real function and read the numbers."""
        import control_app as C
        import self_arming as SA
        rep = {"ok": True, "why": "",
               "locks": [{"lock": "a", "state": "HARDENED", "surface": "X", "acts": "x",
                          "why": "", "n": 9, "k": 9, "wilson": 0.95, "confluence": 2.5},
                         {"lock": "b", "state": "OPEN", "surface": "X", "acts": "x",
                          "why": "", "n": 9, "k": 9, "wilson": 0.90, "confluence": 1.8},
                         {"lock": "c", "state": "UNPROVEN", "surface": "X", "acts": "x",
                          "why": "", "n": 0, "k": 0, "wilson": 0.0, "confluence": 0.0}],
               }
        # ⚠ ROUTES ARE NOT A SEPARATE KEY — _self_arming_state splits ONE `locks` list on
        # `kind == "route"` (control_app.py:15316-15318). My first fixture invented a top-level
        # "routes" key and the test failed 0 != 2: the INSTRUMENT, not the code. Reading the
        # function was one command. [[feedback-suspect-the-instrument]]
        rep["locks"] += [
            {"lock": "r1", "kind": "route", "state": "HARDENED", "surface": "X", "acts": "x",
             "why": "", "n": 9, "k": 9, "wilson": 0.95, "confluence": 2.5},
            {"lock": "r2", "kind": "route", "state": "OPEN", "surface": "X", "acts": "x",
             "why": "", "n": 9, "k": 9, "wilson": 0.90, "confluence": 1.8},
        ]
        was = SA.report
        try:
            SA.report = lambda *a, **k: rep
            got = C._self_arming_state()
        finally:
            SA.report = was
        self.assertEqual(got["open"], 2,
                         "a HARDENED lock must count as open — self_arming.report() counts "
                         "OPEN + HARDENED, and two tallies of one quantity must not disagree")
        self.assertEqual(got["hardened"], 1)
        self.assertEqual(got["routesProven"], 2)


class TheChiliadPanelSpeaksHumanLogic(unittest.TestCase):
    """★ v3283 — CHILIAD WAS A RAW DOCTOR DUMP, AND THE SPLIT IT NEEDED WAS ALREADY IN THE PAYLOAD.

    Grok Bot's brief #5719843089, written for Konyo: CHILIAD should get *"the same treatment as the
    other upgraded sections ... logic that renders, and HUMAN logic — not a raw doctor dump"*, and
    specifically *"separate 'needs Elad' vs 'needs Claude' in the panel (two lists). Eyes keep
    finding fleet-never-asked, missing swept stores, engine/ledger disagree — those must not all
    look the same."* His eyes SAW it as a dump again on LOOKED #5720120566.

    MEASURED on the live console BEFORE writing a line — the backend has named the owner of every
    failing check all along:

        eagle.needsYou 8 · mine 1 · unknown 6
        eagle.mineWhat ["extraction lanes"]
        eagle.say      "8 need you, 6 not measured"

    The panel concatenated all 61 rows into ONE list, so a thing waiting on HIM and a thing waiting
    on CODE arrived looking identical. **This is a join, not a build.** Verified against his live
    payload: WAITING ON YOU 8 · WAITING ON CODE 1 · NOT MEASURED 6 — reproducing the backend's own
    figures exactly, with the 46 ok rows tucked. [[the-unjoined-end]]
    """

    def setUp(self):
        self.src = io.open(UI, encoding="utf-8").read()

    def _sorter(self):
        i = self.src.find("var _mineWhat = {};")
        self.assertGreater(i, -1, "the owner sorter is gone or renamed")
        j = self.src.find("(e.slowRows || []).forEach(_sortRow);", i)
        self.assertGreater(j, i, "the sorter never reaches the slow rows")
        return self.src[i:j + 40]

    def test_the_OWNER_comes_from_the_payload_not_from_a_map_here(self):
        """⚠ The panel must not decide who owns a check. `eagle.mineWhat` is the backend's own
        answer; a private list in the UI would be a second authority that drifts the day a check
        changes hands. [[copy-drift]] [[derived-correctly-from-a-guess]]"""
        blk = self._sorter()
        self.assertIn("e.mineWhat", blk,
                      "the panel no longer reads the backend's owner list, so it is guessing who "
                      "owns each failing check")
        # ⚠ v3337 — RE-ANCHORED. v3326 hoisted the name out: `_mineWhat[String(r && r.check)]`
        # became `_mineWhat[_nm]`. The claim is unchanged — rows are still matched against the
        # backend's owner list by name — but this pinned the SPELLING and went red in CI for
        # eight commits while the pre-push hook (a SUBSET) printed green. This is the FOURTH law
        # that one hoist broke. [[regression-guard]] §4 — pin the LAW, not how it is written.
        self.assertIn("_mineWhat[_nm]", blk,
                      "rows are not matched against the owner list by name")

    def test_a_row_the_backend_calls_MINE_never_lands_in_WAITING_ON_YOU(self):
        """⚠⚠ THE WHOLE POINT. If code's work shows up under 'waiting on you', he is handed a
        chore that was never his — which is the wall the brief asked to end."""
        blk = self._sorter()
        i = blk.find("if (_mineWhat[")
        self.assertGreater(i, -1, "the mine branch is gone")
        self.assertLess(i, blk.find("else if"),
                        "the ownership test is no longer FIRST, so a row that is code's can fall "
                        "into another bucket before it is ever checked")
        self.assertIn("mineRows.push", blk[i:i + 160],
                      "a row the backend calls mine does not go to the code list")

    def test_all_THREE_lists_are_rendered_and_named_in_his_language(self):
        self.assertIn("WAITING ON YOU", self.src, "the list of his own work is gone")
        self.assertIn("WAITING ON CODE", self.src, "the code list is gone — the split is invisible")
        self.assertIn("NOT MEASURED", self.src, "unmeasured checks are not shown as their own thing")
        self.assertNotIn("_vxSection('WHAT NEEDS YOU'", self.src,
                         "the single undifferentiated wall is back")

    def _lead_block(self):
        """The lead's own code, both ends anchored on real bytes.

        ⚠ A FIXED WINDOW BIT ME TWICE IN ONE VERSION. `src[i:i+1100]` reached the sentence until a
        comment was added above it, and then the law went red over code that was correct — a law
        about my guess at a length, not about the file. [[source-window-shortcut]]
        """
        i = self.src.find("var _lead = [];")
        self.assertGreater(i, -1, "the human lead is gone")
        j = self.src.find("return '<div class=\"fxr-win\">'", i)
        self.assertGreater(j, i, "the panel's return is gone — anchor lost")
        return self.src[i:j]

    def test_the_lead_names_the_ERA_from_the_ONE_function_the_footer_uses(self):
        """⚠ The brief: *"footer CHILIAD N should match a clear in-panel 'you are in Chiliad N'"*.
        `window._eraName` is that one function — a second copy of its era table is what its own
        comment warns against."""
        i = self.src.find("var _era = '';")
        self.assertGreater(i, -1, "the era lookup is gone")
        j = self.src.find("var _lead = [];", i)
        self.assertGreater(j, i, "the lead is gone — anchor lost")
        blk = self.src[i:j]
        self.assertIn("window._eraName", blk,
                      "the panel computes the era itself instead of asking the function the "
                      "footer paints from, so the two can now disagree")

    def test_a_ZERO_is_said_out_loud_not_omitted(self):
        """⚠ "nothing is waiting on you" is the answer he came for. An empty list that simply
        vanishes reads as "not measured". [[zero-needs-a-denominator]]"""
        blk = self._lead_block()
        self.assertIn("nothing is waiting on you", blk,
                      "a zero on his own list disappears instead of being stated")
        self.assertIn("everything was measured", blk,
                      "a zero on the unmeasured list disappears instead of being stated")

    def test_the_headline_figures_come_from_the_COUNTER_not_the_list_lengths(self):
        """⚠ A pre-existing law in test_control pins that this builder reads `e.needsYou`, and it
        is the right rule: `e.needsYou` is what the eagle COUNTED, while a list length is what the
        panel managed to RENDER. Quoting the second as though it were the first would hide a row
        the panel dropped."""
        blk = self._lead_block()
        for f in ("e.needsYou", "e.mine", "e.unknown"):
            self.assertIn(f, blk,
                          "the lead no longer quotes %s, so its headline is the panel's own "
                          "rendering rather than the counter's finding" % f)
        self.assertIn("youRows.length", blk,
                      "there is no fallback when the payload omits the count, so a missing figure "
                      "would print as undefined")

    def test_a_DISAGREEMENT_between_the_counter_and_the_panel_is_said_out_loud(self):
        """★ v3284 — raised by the cross-family eye on v3283, and real.

        The headline counts come from the payload (`e.needsYou` etc.) while the lists are bucketed
        client-side, so the panel could read *"8 thing(s) are waiting on YOU"* above **seven** rows
        with nothing to explain the missing one. Silence there is the worst outcome: he either
        trusts a number with no referent, or distrusts a list that is correct.

        ⚠ NEITHER FIGURE IS DROPPED. The counter's number leads, because it is what the eagle
        measured; the rendered number follows when they differ, because that is what he can see.
        A gap is a finding ABOUT THE PANEL, not a reason to hide one of the two.
        Verified in node: agreeing renders no warning, `8 vs 7` renders
        "⚠ the counter and this panel disagree (you 8 vs 7 shown)".
        [[zero-needs-a-denominator]] [[label-outlived-referent]]
        """
        blk = self._lead_block()
        self.assertIn("var _gap = []", blk, "the panel no longer compares its lists to the counts")
        for pair in ("_nYou !== youRows.length", "_nMine !== mineRows.length",
                     "_nUnk !== unkRows.length"):
            self.assertIn(pair, blk, "%s is not compared, so that list can drift silently" % pair)
        self.assertIn("disagree", blk,
                      "a mismatch between the counter and the panel is not said out loud")

    def test_the_machine_detail_is_TUCKED_not_deleted(self):
        """⚠ The brief said *"doctor rows either rewritten or TUCKED"* — tucked, not lost. Versions,
        fleet and disk stay one click away."""
        # ⚠ `open` is load-bearing, not cosmetic: a CLOSED <details> gives its children zero
        # height, and `state-panel` PHOTOGRAPHS these sections — the render gate refused the first
        # cut with "31 element(s) have text cut off ... cut by fxr-win" at all five widths.
        # Collapsing them by default would retire them from visual supervision, silently.
        self.assertIn('<details class="vx-fold" open>', self.src,
                      "the machine-detail fold is closed by default, which zero-heights every "
                      "section the render gate photographs")
        i = self.src.find('<details class="vx-fold" open>')
        blk = self.src[i:i + 700]
        for sec in ("VERSIONS", "THE FLEET", "DISK"):
            self.assertIn(sec, blk, "%s was dropped rather than tucked" % sec)

    def test_every_class_the_lead_emits_is_styled(self):
        """⚠ this repo already has a law for the shelf's builder; the same rule applies here — a
        class nobody styles is a flag nobody can see."""
        for cls in ("vx-lead", "vx-lead-l", "vx-lead-v", "vx-lead-s", "vx-fold"):
            self.assertIn("#ver-xref ." + cls, self.src,
                          "the panel emits .%s and nothing styles it" % cls)


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
