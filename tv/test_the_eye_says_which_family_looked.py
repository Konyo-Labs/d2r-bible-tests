# -*- coding: utf-8 -*-
"""v2766 — A DARK EYE AND AN ABSENT ONE LOOKED IDENTICAL ON THE FLEET.

MEASURED before the change, off the live beacon:

    Konyo  eye={"live": false, "ageMs": 0}
    Dean   eye={"live": false, "ageMs": 63824123}

and the card rendered the glyph ONLY when `live` was true, so three different machines drew the
same nothing:

    · no second model family is INSTALLED there   (Dean — correct and expected)
    · one is installed and IDLE                   (Konyo, lane toggled off)
    · one is installed, on, and FAILING

Absence, rest and failure are not the same fact. [[zero-needs-a-denominator]]

=== ⚠ WHAT THIS IS *NOT* ===
The task that produced this file was first written as "make the eye provider-neutral", and that was
WRONG — it already is, and the correction is kept here because writing it before measuring is the
error worth remembering:

    chronicle_hunt.py   lane = (page or {}).get("lane") or "claude"   <- Claude IS the default
    chronicle_hunt.py   ZERO grok references anywhere in the reader
    control_app.py      "GROK EYES (G5) — REMOVABLE. OFF by default." + a removal checklist

Konyo's ruling — *"grok doesnt exist for dean.. it all needs to be claude based.. default as if
shadow is off toggled off"* — was ALREADY the built behaviour. Nothing was rebuilt. The only real
gap was that none of it reached the WIRE, so the card could not say which of the three states a
dark dot meant.

=== ⚠⚠ AVAILABILITY IS NOT A SECOND EYE, AND THIS FILE GUARDS THAT ===
A machine reporting a second family has a lane that COULD look. It has not looked. Only
`second_eye_ledger` records a look, and it refuses same-family ones on purpose so a model cannot
certify its own work. If a Claude run on Dean's box ever banked as a "second eye", the ledger would
report a filled seat that is empty — worse than no ledger at all.

    CHECK      any model, anywhere, including Claude on Dean's box. Bankable as a check.
    SECOND EYE a DIFFERENT family from the author. Where none exists the honest state is an
               EMPTY SEAT, said out loud.

[[grok-second-eye]] [[feedback-silence-is-not-evidence]] [[workflow-third-eye-provider-neutral]]
"""
import io
import json
import os
import tempfile
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import control_app as CA  # noqa: E402

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
APP = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()


def _render(cases):
    """Run the SHIPPED _fleetEye in node. -> dict|None

    ⚠ THE REAL BUILDER, not a re-description of it. `escC` is stubbed because it belongs to the
    console's own escaping rules, which this file does not own and must not restate.
    """
    i = UI.find("      var _fleetEye = function(e){")
    j = UI.find("      window._fleetEye = _fleetEye;", i)
    if i < 0 or j < 0:
        raise AssertionError("REG-1900 - the subject this harness drives is gone (_fleetEye): a renamed subject is a FAILURE, never a skip")
    js = ("var window = {};\n"
          "var escC = function(s){ return String(s === undefined ? '' : s)"
          ".replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); };\n"
          + UI[i:j] + "\n"
          "const cases = " + json.dumps(cases) + ";\n"
          "const out = {}; for (const k in cases) out[k] = _fleetEye(cases[k]);\n"
          "console.log(JSON.stringify(out));")
    p = os.path.join(tempfile.gettempdir(), "fleet_eye_probe.js")
    io.open(p, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run(["node", p], capture_output=True, text=True, timeout=90)
    except FileNotFoundError:
        return None          # REG-1900 - the ONE skip: there is no node on this venue
    if r.returncode != 0:    # the subject would not run: that is the subject's failure, not the venue's
        raise AssertionError("REG-1900 - the shipped code would not run in node: %s" % (r.stderr or "")[-400:])
    return json.loads((r.stdout or "").strip().split("\n")[-1])


class TheEyeSaysWhichFamilyLooked(unittest.TestCase):

    # ── ⚠⚠ THE WIRE ─────────────────────────────────────────────────────────────────────────
    def test_the_wire_carries_the_provider_and_the_family(self):
        e = CA._eye_for_wire()
        if e is None:
            self.skipTest("the eye pulse did not run here, so there is no payload to grade — "
                          "a skip is NOT a pass")
        self.assertEqual("claude", e.get("provider"),
                         "the wire does not say WHO read, so a consumer has to assume it")
        self.assertEqual("anthropic", e.get("family"))
        self.assertIn("second", e, "the wire says nothing about a second family, which is the "
                                   "whole gap: absence, rest and failure stay indistinguishable")

    #: v2770 — SIX, NOT FOUR. `on` used to swallow "on and failing" and `absent` used to swallow
    #: "installed, nobody signed in". Both are separate facts with separate things to do about them.
    _STATES = ("absent", "unauthorised", "off", "on", "failing", "unknown")
    #: every state except the two that are simply working needs a sentence: a bare label leaves him
    #: guessing whether a dark chip is a correct machine, a switch, or a fault.
    _MUST_EXPLAIN = ("absent", "unauthorised", "failing", "unknown")

    def test_the_second_lane_state_is_one_of_the_six(self):
        st = CA._second_eye_lane_state()
        self.assertIn(st.get("state"), self._STATES)
        if st["state"] in self._MUST_EXPLAIN:
            self.assertTrue(st.get("why"),
                            "the lane is %r and nothing says why — an unexplained absence reads "
                            "as a fault when on most machines it is simply correct" % st["state"])

    def test_a_lane_that_is_ON_AND_FAILING_is_not_reported_as_ON(self):
        """★★ THE DEFECT THIS ROUND EXISTS FOR. `state` was `"on" if st.get("on") else "off"`, so
        the case g5_grok_eyes was built to publish — MEASURED live on his console at 165 calls,
        107 errors, `last_error` a 402 Payment Required, `intentBlocked` true — reached the fleet
        card as an ordinary lit second lane. The far end had refused permanently and the chip said
        the lane was on. A failure wearing health is worse than no chip.

        ⚠ THE PROBE REPLACES `g5_grok_eyes.status`, NOT the function under test. Asserting on a
        re-description of the branch would pass over a deleted branch.
        """
        import g5_grok_eyes as g5
        orig = g5.status
        base = {"cliInstalled": True, "authorized": True, "on": True, "mode": "primary",
                "stats": {"last_error": "grok exit 1: 402 Payment Required"}}
        try:
            g5.status = lambda: dict(base, intentBlocked=True,
                                     blockedWhy="the far end answered 402 Payment Required")
            st = CA._second_eye_lane_state()
            self.assertEqual("failing", st.get("state"),
                             "an installed, signed-in, switched-on lane that the far end is "
                             "refusing reports %r — indistinguishable from a healthy one"
                             % st.get("state"))
            self.assertIn("402", st.get("why") or "",
                          "the failure carries no reason, so the card can only say something is "
                          "wrong without saying what")

            # ⚠ AND THE HONESTY FIELD IS SOMETIMES EMPTY — that is exactly the v1767 case. An
            # unexplained failure is still a failure; it must not fall back to "on".
            g5.status = lambda: dict(base, intentBlocked=True, blockedWhy="")
            st = CA._second_eye_lane_state()
            self.assertEqual("failing", st.get("state"))
            self.assertIn("402", st.get("why") or "",
                          "blockedWhy was empty and last_error was not consulted, so a real "
                          "failure is reported with no reason at all")

            # ⚠⚠ AND THAT FALLBACK CARRIES MACHINE TEXT ONTO ANOTHER MACHINE. `last_error` is
            # `str(e)[:160]` — an exception naming an absolute path is ordinary — and this dict
            # rides the console beacon to THE FLEET, so it is read on Dean's box. A reason he can
            # act on does not need to name a home directory.
            g5.status = lambda: dict(
                base, intentBlocked=True, blockedWhy="",
                stats={"last_error": "grok exit 1: cannot open /Users/someone/secretdir/x.json"})
            why = CA._second_eye_lane_state().get("why") or ""
            self.assertNotIn("/Users/", why,
                             "a raw home path is being published to the fleet: %r" % why)
            self.assertIn("~", why, "the path was dropped entirely rather than redacted, so the "
                                    "reason lost the shape of what failed")
            self.assertLessEqual(len(why), 160,
                                 "an unbounded error string is riding the beacon")

            # a lane the switch is not asking for is RESTING, never faulty
            g5.status = lambda: dict(base, on=False, mode="off", intentBlocked=False,
                                     blockedWhy="")
            self.assertEqual("off", CA._second_eye_lane_state().get("state"),
                             "a lane toggled off is being reported as a fault")
            g5.status = lambda: dict(base, intentBlocked=False, blockedWhy="")
            self.assertEqual("on", CA._second_eye_lane_state().get("state"))
        finally:
            g5.status = orig

    def test_INSTALLED_BUT_NOT_SIGNED_IN_is_not_the_same_fact_as_ABSENT(self):
        """★★ `if not cliInstalled or not authorized` collapsed two different machines into one
        label, and the rendered sentence contradicted itself inside a single bracket:

            no second model family on this machine (nobody is signed in)

        `absent` is a MEASUREMENT — Dean's box genuinely has none, which is correct and expected
        and must never look broken. Not-signed-in is one click from working. Different fact,
        different thing to do, different state. [[zero-needs-a-denominator]]"""
        import g5_grok_eyes as g5
        orig = g5.status
        try:
            g5.status = lambda: {"cliInstalled": True, "authorized": False, "needsLogin": True,
                                 "on": False, "intentBlocked": False, "blockedWhy": ""}
            st = CA._second_eye_lane_state()
            self.assertEqual("unauthorised", st.get("state"),
                             "a CLI that is present but not signed in reports %r" % st.get("state"))
            self.assertNotIn("not installed", (st.get("why") or "").lower(),
                             "the reason still says the thing is not installed, which is the "
                             "self-contradiction this split exists to remove")

            g5.status = lambda: {"cliInstalled": False, "authorized": False, "needsInstall": True,
                                 "on": False, "intentBlocked": False, "blockedWhy": ""}
            st = CA._second_eye_lane_state()
            self.assertEqual("absent", st.get("state"))
            self.assertNotIn("signed in", (st.get("why") or "").lower(),
                             "a machine with no second family at all is being told nobody signed "
                             "in to it — there is nothing to sign in to")
        finally:
            g5.status = orig

    def test_an_UNREACHABLE_lane_is_UNKNOWN_and_never_absent(self):
        """★ THE DISTINCTION THAT MATTERS MOST. "not installed" is a MEASUREMENT; "I could not ask"
        is not. Collapsing the second into the first would tell Konyo a cousin has no second family
        when the truth is nobody looked. [[unknown-stays-unknown]]"""
        src = APP[APP.find("def _second_eye_lane_state():"):]
        src = src[:src.find("\ndef ", 1)]
        self.assertIn("except ImportError:", src,
                      "the lane does not separate 'not installed' from 'could not be asked'")
        self.assertIn('state="absent"', src)
        # ⚠⚠ EVERY RAISED-EXCEPTION HANDLER, AND ANCHORED AT BOTH ENDS. This law used to read
        # `src[i:i + 400]` from the FIRST `except Exception as exc:` — two defects in one line.
        # A fixed character window reports anything past its 400th byte as ABSENT, and there are
        # TWO such handlers (the import and the status call): a sabotage that made the SECOND one
        # return a measured absence sailed straight through, because the law had only ever looked
        # at the first. [[source-reading-guard]] [[sabotage-is-usually-the-wrong-one]]
        starts = [m.start() for m in re.finditer(r"except Exception as exc:", src)]
        self.assertGreaterEqual(len(starts), 2,
                                "only %d raised-exception handlers found — the import probe and "
                                "the status call each need one, so a failure somewhere is being "
                                "reported as a measurement" % len(starts))
        for i in starts:
            j = src.find("return out", i)
            self.assertGreater(j, i, "a raised-exception handler never returns, so its extent "
                                     "cannot be established and this law would measure a guess")
            self.assertNotIn('state="absent"', src[i:j],
                             "a lane that RAISED is being reported as absent — a failed probe "
                             "rendering as a measured 'none'")

    def test_the_none_contract_is_UNTOUCHED(self):
        """⚠ `_eye_for_wire()` returns None when the pulse did not run, and an existing law
        (test_control) pins that. Adding fields must not turn UNKNOWN into a payload."""
        i = APP.find("def _eye_for_wire():")
        blk = APP[i:APP.find("\ndef ", i + 1)]
        self.assertIn("return None", blk,
                      "the pulse-did-not-run case stopped returning None, so an unmeasured eye "
                      "now ships a payload and reads as measured")

    def test_it_does_NOT_keep_its_own_family_table(self):
        """★ `second_eye_ledger.family_of` is the authority that ENFORCES the cross-family rule. A
        second table here would be free to drift from it, and the wire would then name a family the
        ledger does not recognise. [[copy-drift]]"""
        i = APP.find("def _second_eye_lane_state():")
        blk = APP[i:APP.find("\ndef _eye_for_wire", i)]
        self.assertIn("second_eye_ledger", blk, "the lane state does not consult the family authority")
        # ⚠ FORBID THE FAMILY LITERAL, NOT A TABLE SHAPE. My first cut asserted `"xai":` was absent
        # — a family name in KEY position — and a sabotage writing `{"grok": "xai"}` sailed straight
        # through it, because there the family is the VALUE. A guard aimed at one spelling of a
        # defect measures that spelling and nothing else. No family name may be written here at
        # all; the ledger is the only place they are allowed to live.
        for fam in ('"xai"', "'xai'", '"anthropic"', "'anthropic'", '"openai"', "'openai'"):
            self.assertNotIn(fam, blk,
                             "the family name %s is hardcoded beside the ledger that enforces the "
                             "cross-family rule. Two tables drift, and then the wire names a "
                             "family the ledger does not recognise." % fam)

    # ── ⚠⚠ THE CARD ─────────────────────────────────────────────────────────────────────────
    #: the six cases, in one place, so the render laws below cannot drift apart from each other
    _CASES = {
        "absent": {"live": False, "ageMs": 63824123, "provider": "claude",
                   "second": {"state": "absent", "provider": "grok",
                              "why": "the second-family CLI is not installed on this machine"}},
        "unauthorised": {"live": False, "ageMs": 4000, "provider": "claude",
                         "second": {"state": "unauthorised", "provider": "grok",
                                    "why": "installed here but nobody is signed in"}},
        "off": {"live": False, "ageMs": 0, "provider": "claude",
                "second": {"state": "off", "provider": "grok"}},
        "on": {"live": True, "ageMs": 1200, "provider": "claude",
               "second": {"state": "on", "provider": "grok"}},
        "failing": {"live": True, "ageMs": 1200, "provider": "claude",
                    "second": {"state": "failing", "provider": "grok",
                               "why": "the far end answered 402 Payment Required"}},
        "unknown": {"live": False, "ageMs": 5000, "provider": "claude",
                    "second": {"state": "unknown", "why": "raised TimeoutError"}},
    }

    def test_the_six_states_render_DIFFERENTLY(self):
        got = _render(self._CASES)
        if got is None:
            self.skipTest("node unavailable, so the shipped builder could not be run — a skip is "
                          "NOT a pass")
        self.assertIn("no second model family on this machine", got["absent"])
        self.assertIn("not installed on this machine", got["absent"],
                      "the absence does not say WHY, so a correct machine looks broken")
        self.assertIn("toggled off", got["off"])
        self.assertIn("second model family grok ON", got["on"])
        # v3887 (REG-3477) - three eyes on a row: this one's hover says it is the FRAME READER, and never calls the other family
        # a "second lane" beside the window eye (GrokBot: "if the second eye means console window up ... if it means the grok lane")
        for k, h in got.items():
            self.assertIn('title="frame reader: claude', h, "%s: the capture eye's hover does not say which eye it is" % k)
            self.assertNotIn("second lane", h, "%s: 'second lane' again, beside the window eye he calls the second" % k)
        self.assertIn("UNKNOWN", got["unknown"],
                      "a lane nobody could ask renders as a settled state")
        self.assertNotEqual(got["absent"], got["off"],
                            "an ABSENT second family and an IDLE one render identically — the "
                            "exact defect this file exists for")
        self.assertIn("fleet-eye-dark", got["absent"])
        self.assertIn("fleet-eye-live", got["on"])
        # ⚠⚠ NO TWO OF THE SIX MAY SHARE A RENDERING. Pairwise, not one-by-one: the first cut of
        # this file asserted a phrase per state and a state that quietly fell through to the
        # `else` branch could still satisfy every individual assertion.
        names = list(self._CASES)
        pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if got[a] == got[b]]
        self.assertEqual([], pairs,
                         "these states are indistinguishable on screen: %s. Absence, rest, "
                         "failure and 'nobody asked' are different facts." % pairs)
        # ⚠ AND THE SENTENCE HE ACTUALLY READS MUST DIFFER, not merely the markup. Comparing whole
        # HTML strings was too weak on its own: a sabotage that gave FAILING the healthy lane's
        # exact wording still produced different HTML, because the CSS class alone still differed
        # — and a class is not something he can read. The tooltip is the text.
        def _title(h):
            return h.split('title="', 1)[1].split('"', 1)[0] if 'title="' in h else h
        tpairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
                  if _title(got[a]) == _title(got[b])]
        self.assertEqual([], tpairs,
                         "these states say the IDENTICAL sentence: %s. Only a CSS class separates "
                         "them, and a class cannot be read, hovered or screenshotted." % tpairs)
        # ⚠⚠ AND THE OTHER HALF: two states must not share a LOOK either. v2766's CSS comment
        # promised "an absent lane is dimmer still and loses its colour entirely" and no such class
        # was ever written — `absent` and `off` both fell through to `.fleet-eye-dark` and were
        # pixel-identical, while every string assertion here passed because their titles differ.
        # Found by rendering all six side by side and LOOKING. [[visual-regression-detector]]
        def _cls(h):
            return frozenset(h.split('class="', 1)[1].split('"', 1)[0].split())
        cpairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
                  if _cls(got[a]) == _cls(got[b])]
        self.assertEqual([], cpairs,
                         "these states are styled IDENTICALLY: %s. Their tooltips differ, so every "
                         "text assertion passes while the two chips are the same pixels — which is "
                         "the defect this whole file exists for, one layer down." % cpairs)

    def test_a_FAILING_second_lane_does_not_wear_the_healthy_one_s_look(self):
        """★★ The whole point. `on` and `failing` both have a second family present, so the ² is
        right for both — everything else about them must differ, INCLUDING without colour."""
        got = _render(self._CASES)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertIn("FAILING", got["failing"],
                      "a lane the far end is refusing does not say so")
        self.assertIn("402 Payment Required", got["failing"],
                      "the failure gives him nothing to act on")
        self.assertNotIn("fleet-eye-two\"", got["failing"],
                         "the failing lane is wearing the healthy lane's class, so it is styled "
                         "as a working second eye")
        self.assertIn("fleet-eye-two-bad", got["failing"])
        # ⚠ COLOUR IS NOT THE ONLY CHANNEL. A greyscale screenshot, a colour-blind reader and a
        # copy-paste of the glyph all lose the class; the difference has to survive in the text.
        _glyph = lambda h: h.split(">")[1].split("<")[0]
        self.assertNotEqual(_glyph(got["on"]), _glyph(got["failing"]),
                            "healthy and failing draw the identical glyph %r, so the only thing "
                            "separating them is a CSS class" % _glyph(got["on"]))

    def test_NOT_SIGNED_IN_never_renders_as_NO_SECOND_FAMILY(self):
        """★ The self-contradicting sentence, pinned. The old wording produced, in one bracket,
        `no second model family on this machine (nobody is signed in)`."""
        got = _render(self._CASES)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertNotIn("no second model family on this machine", got["unauthorised"],
                         "a machine that HAS the second family and is merely signed out is being "
                         "told it has none — and then told, in the same sentence, that nobody is "
                         "signed in to the thing that supposedly is not there")
        self.assertIn("NOT SIGNED IN", got["unauthorised"],
                      "the one actionable fact — one click on Authorize — is missing")
        self.assertNotEqual(got["unauthorised"], got["absent"])

    def test_no_pulse_renders_NOTHING_rather_than_a_dot(self):
        got = _render({"none": None})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertEqual("", got["none"],
                         "an omitted eye field drew a chip anyway, so UNKNOWN is being rendered "
                         "as a measured state")

    def test_availability_is_never_worded_as_a_LOOK(self):
        """★★ THE SAFETY LAW. A lane that COULD look has not looked. If this chip ever reads as a
        completed second eye, the empty seat starts reporting as filled — worse than no ledger."""
        i = UI.find("      var _fleetEye = function(e){")
        blk = UI[i:UI.find("      window._fleetEye = _fleetEye;", i)]
        for banned in ("verified", "second eye", "reviewed", "confirmed", "checked by"):
            self.assertNotIn(banned, blk.lower(),
                             "the fleet eye chip says %r. Availability is not a look, and only "
                             "second_eye_ledger records one." % banned)

    def test_the_builder_and_its_caller_share_a_SCRIPT_BLOCK(self):
        """⚠ control_ui.html has more than one <script>, and a call across them is a DEAD RENDER —
        five times in this file's history. This is cheap to assert and impossible to eyeball."""
        blocks = [(m.start(), UI.index("</script>", m.start()))
                  for m in re.finditer(r"<script[^>]*>", UI)]

        def blk_of(pos):
            for n, (a, b) in enumerate(blocks):
                if a <= pos <= b:
                    return n
            return None
        d = UI.find("var _fleetEye = function(e){")
        c = UI.find("+ _fleetEye(m.eye)")
        self.assertGreater(d, 0, "the builder is gone")
        self.assertGreater(c, 0, "the fleet row no longer calls the builder")
        self.assertIsNotNone(blk_of(d), "the builder is not inside any <script>")
        self.assertEqual(blk_of(d), blk_of(c),
                         "the builder and its caller are in DIFFERENT script blocks — the chip "
                         "would silently render nothing")
        self.assertLess(d, c, "the builder is defined after its caller")



RED_PROOF = [
    {"why": "v3887 (REG-3477) - the capture eye's hover no longer says it is the frame reader (three eyes, one unnamed)",
     "file": "tv/control_ui.html",
     "find": "escC('frame reader: ' + prov + ' \\u00b7 ' + when + stail)",
     "replace": "escC(prov + ' \\u00b7 ' + when + stail)",
     "matches": 1, "needs": "node"},
    {
        'why': 'The only place _second_eye_lane_state() names the FAILING state is the intentBlocked branch in tv/control_app.py — a lane the far end is permanently refusing (402 Payment Required, intentBlocked true). Rewriting that single occurrence to state="on" restores the exact v2770 defect: an installed, signed-in, switched-on but refused second lane is republished to THE FLEET as an ordinary healthy second eye, so failure wears health. It is not a comment, not a message string, and not a constant both sides of an agreement read — the render laws use hardcoded _CASES, so only the wire law moves.  MEASURED: untampered perl -e \'alarm 200; exec @ARGV\' python3 tv/test_the_eye_says_which_family_looked.py -> Ran; tampered (all 1) Same command after replacing all 1 occurrence -> Ran 13 tests, FAILED (failures=1): test_a; reddened law test_the_eye_says_which_family_looked.TheEyeSaysWhichFamilyLooked.test; ALONE python3 -m unittest test_the_eye_says_which_family_looked.TheEyeSaysWhichFamilyLooked.test_a_lane_that_is_ON_A.',
        'file': 'control_app.py',
        'find': 'state="failing"',
        'replace': 'state="on"',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
