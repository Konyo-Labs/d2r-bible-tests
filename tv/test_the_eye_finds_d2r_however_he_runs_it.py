# -*- coding: utf-8 -*-
"""#232 — THE EYE FINDS DIABLO II: RESURRECTED HOWEVER HE RUNS IT, AND ONLY THE GAME.

HIS ORDER, 2026-09-24: "needs to target diablo ii resurrected in macbook like it is crossover or
nvideaplay chrome or boosteroid so windows also regularly for those options + the usual route on
windows locally. and linux cant open those they lock automatically".

MEASURED before this: on the Mac every browser was blocked wholesale, so a GeForce NOW session in a
Chrome tab could never pin; on Windows capture_win.ps1 only enumerated D2R-process windows, so a
streamed session fell through to FULL SCREEN and filmed the desktop. And a store-style title,
"Diablo® II: Resurrected™", never matched "diablo ii" because of the ®.

DRIVEN on the pure picker (game_route + score_d2r_window_candidate) and, for Windows, on the
C# source the script compiles (its routes are asserted by text here and COMPILED on the Windows box
over SSH; a Mac cannot run Add-Type). ⚠ The real cloud window titles are UNMEASURED: the cases below
use the shape the services are expected to show, and a service window whose title does NOT name the
game is a near-miss the picker reports rather than pins. RED_PROOF below.
"""
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

import tv_diablo as tv  # noqa: E402

W, H = 1470, 956


class TheMacFindsEveryRoute(unittest.TestCase):

    def test_local_and_crossover_still_pin(self):
        self.assertEqual(tv.game_route("D2R.exe", "Diablo II: Resurrected"), "local")
        self.assertEqual(tv.game_route("CrossOver", "Diablo II: Resurrected"), "crossover")
        self.assertIsNotNone(tv.score_d2r_window_candidate("D2R.exe", "Diablo II: Resurrected", W, H))

    def test_geforce_now_in_its_app_or_a_browser_tab_pins(self):
        for owner, title in (("GeForceNOW", "Diablo® II: Resurrected™"),
                             ("Google Chrome", "Diablo® II: Resurrected™ on GeForce NOW"),
                             ("Microsoft Edge", "GeForce NOW - Diablo II: Resurrected"),
                             # MEASURED on his screen 2026-09-24 — the first real streamed title
                             ("Google Chrome", "Diablo II: Resurrected \u2013 Infernal Edition on GeForce NOW")):
            self.assertEqual(tv.game_route(owner, title), "geforce-now", "%s %r" % (owner, title))
            self.assertIsNotNone(tv.score_d2r_window_candidate(owner, title, W, H),
                                 "a streamed D2R window (%s %r) could not pin" % (owner, title))

    def test_boosteroid_in_its_app_or_a_browser_tab_pins(self):
        for owner, title in (("Boosteroid", "Diablo II: Resurrected"),
                             ("Google Chrome", "Boosteroid - Diablo II: Resurrected")):
            self.assertEqual(tv.game_route(owner, title), "boosteroid", "%s %r" % (owner, title))
            self.assertIsNotNone(tv.score_d2r_window_candidate(owner, title, W, H))

    def test_a_browser_needs_BOTH_the_service_and_the_game(self):
        for owner, title in (("Google Chrome", "Diablo II: Resurrected build guide"),   # no service
                             ("Google Chrome", "GeForce NOW"),                          # no game
                             ("Safari", "Boosteroid Cloud Gaming")):                    # no game
            self.assertIsNone(tv.score_d2r_window_candidate(owner, title, W, H),
                              "%s %r pinned as the game" % (owner, title))

    def test_a_service_window_without_the_game_is_a_named_near_miss(self):
        self.assertEqual(tv.game_route("Google Chrome", "GeForce NOW"), "near:geforce-now")
        # 2026-09-27 — MEASURED on his ALT: Boosteroid's own app is titled "Boosteroid" and nothing else while a
        # game streams, so that one bare title pins (test_a_windows_door_sees_the_game.py). A tab never does.
        self.assertEqual(tv.game_route("Google Chrome", "Boosteroid"), "near:boosteroid")
        self.assertEqual(tv.game_route("Boosteroid", "Boosteroid Launcher"), "near:boosteroid")

    def test_the_marks_a_store_puts_in_the_name_do_not_hide_it(self):
        self.assertEqual(tv._norm_title("Diablo®  II: Resurrected™"), "diablo ii: resurrected")


class TheSecondEyeOnV3496(unittest.TestCase):
    """#232 — grok-4.7 on v3496, every case reproduced before it was fixed."""

    def test_a_game_word_is_a_word(self):
        for title in ("GeForce NOW - Resurrected", "GeForce NOW - Diablo 2024"):
            self.assertEqual(tv.game_route("Google Chrome", title), "near:geforce-now",
                             "%r was taken for the game" % title)
        self.assertEqual(tv.game_route("Google Chrome", "Boosteroid - ranked d2races"), "near:boosteroid")

    def test_a_browser_is_its_whole_name(self):
        for owner in ("Archive Utility", "Operational Log"):
            self.assertIsNone(tv.game_route(owner, "GeForce NOW Diablo II"),
                              "%r was treated as a browser tab" % owner)
        self.assertEqual(tv.game_route("Opera", "Boosteroid | Diablo II: Resurrected"), "boosteroid")

    def test_a_title_naming_two_services_is_never_pinned_as_the_first(self):
        t = "GeForce NOW - Boosteroid - Diablo II: Resurrected"
        self.assertEqual(tv.game_route("Google Chrome", t), "near:ambiguous")
        self.assertIsNone(tv.score_d2r_window_candidate("Google Chrome", t, W, H))

    def test_the_scorer_normalizes_before_it_judges(self):
        self.assertEqual(tv.game_route("CrossOver", "Diablo\u00ae II"), "crossover")
        self.assertIsNotNone(tv.score_d2r_window_candidate("CrossOver", "Diablo\u00ae II", W, H),
                             "game_route called it the game and the scorer refused it - one module, two answers")

    def test_his_measured_title_still_pins(self):
        t = "Diablo II: Resurrected \u2013 Infernal Edition on GeForce NOW"
        self.assertEqual(tv.game_route("Google Chrome", t), "geforce-now")
        self.assertIsNotNone(tv.score_d2r_window_candidate("Google Chrome", t, W, H))


class TheMacPickerOnAFakeScreen(unittest.TestCase):
    """find_d2r_window_mac() itself, over a stubbed Quartz window list (never his real screen)."""

    def _screen(self, wins):
        import types
        q = types.ModuleType("Quartz")
        q.kCGWindowListOptionAll, q.kCGNullWindowID = 0, 0
        q.CGWindowListCopyWindowInfo = lambda *a: [
            {"kCGWindowLayer": 0, "kCGWindowOwnerName": o, "kCGWindowName": t,
             "kCGWindowBounds": {"Width": W, "Height": H}, "kCGWindowIsOnscreen": True,
             "kCGWindowNumber": 100 + i} for i, (o, t) in enumerate(wins)]
        if not hasattr(self, "_saved"):       # the FIRST call's state is what tearDown restores
            self._saved = ("Quartz" in sys.modules, sys.modules.get("Quartz"), tv._PICK_CACHE, tv.sys.platform)
        sys.modules["Quartz"] = q
        tv._PICK_CACHE = None
        tv.sys.platform = "darwin"

    def tearDown(self):
        # ⚠ the second eye on v3496: this used to discard the saved cache and pop a REAL Quartz a
        # method never replaced. It restores exactly what _screen found, and touches nothing if
        # _screen never ran.
        if not hasattr(self, "_saved"):
            return
        had, q, cache, plat = self._saved
        if had:
            sys.modules["Quartz"] = q
        else:
            sys.modules.pop("Quartz", None)
        tv._PICK_CACHE, tv.sys.platform = cache, plat

    def test_a_streamed_window_pins_with_its_route_on_the_label(self):
        self._screen([("Finder", "tv-diablo-mailbox"), ("GeForceNOW", "Diablo\u00ae II: Resurrected\u2122")])
        hit = tv.find_d2r_window_mac()
        self.assertIsNotNone(hit, "the GeForce NOW window streaming D2R was not pinned")
        self.assertTrue(hit[1].startswith("GeForce NOW"), "the route is not on the label: %r" % (hit,))

    def test_a_service_window_without_the_game_is_reported_not_pinned(self):
        self._screen([("Google Chrome", "GeForce NOW"), ("Finder", "d2r notes")])
        self.assertIsNone(tv.find_d2r_window_mac())
        self.assertIn("geforce-now", tv._PICK_WHY, "the near-miss was not named: %r" % tv._PICK_WHY)

    def test_a_cloud_window_naming_the_game_that_cannot_pin_is_named(self):
        # the title block now applies to a streamed title too: the launcher on GeForce NOW
        self._screen([("Google Chrome", "Battle.net - Diablo II: Resurrected on GeForce NOW")])
        self.assertIsNone(tv.find_d2r_window_mac())
        self.assertIn("names the game but is not pinnable", tv._PICK_WHY,
                      "a cloud window naming the game was dropped with the generic why: %r" % tv._PICK_WHY)

    def test_linux_pins_nothing_and_says_why(self):
        self._screen([("GeForceNOW", "Diablo II: Resurrected")])
        tv.sys.platform = "linux"
        self.assertIsNone(tv.find_d2r_window_mac())
        self.assertIn("Linux", tv._PICK_WHY)


class WindowsFindsEveryRoute(unittest.TestCase):
    """capture_win.ps1's C# finder — asserted on its source here, compiled on the Windows box."""

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "capture_win.ps1"), encoding="utf-8-sig").read()

    def test_the_cloud_apps_and_browsers_are_candidates(self):
        self.assertRegex(self.src, r'CloudApps = new string\[\] \{ "GeForceNOW", "Boosteroid" \}')
        self.assertIn('"chrome", "msedge"', self.src)
        self.assertIn("public static string CloudRoute(string proc, string title, bool browser)", self.src)

    def test_a_service_window_that_does_not_name_the_game_is_skipped(self):
        code = "\n".join(l.split("//", 1)[0] for l in self.src.split("\n"))
        # re-anchored (the second eye on 757518cc): the skip is a block now, and it records the near-miss
        i = code.find('if (route == "") {')
        self.assertGreater(i, -1, "a browser or cloud-app window that does not name the game became a candidate")
        self.assertIn("return true;", code[i:code.find("}", i + 1)],   # bounded by the block's own brace
                      "a browser or cloud-app window that does not name the game became a candidate")

    def test_the_windows_twin_reads_words_and_refuses_two_services(self):
        code = "\n".join(l.split("//", 1)[0] for l in self.src.split("\n"))
        self.assertIn('Regex(@"\\bdiablo\\s*(?:ii|2)\\b|\\bd2r\\b")', code, "the C# game words drifted from _GAME_RX")
        self.assertIn("return GameRx.IsMatch(tl);", code)
        self.assertIn('if (gfn && bst) return "";', code, "a title naming two services pins as the first one")

    def test_windows_holds_the_eye_instead_of_filming_the_desktop(self):
        """the second eye on 757518cc: with nothing pinned, auto filmed the WHOLE DESKTOP even with no D2R at
        all; the Mac holds the eye (v1251). Source-pinned: the loop runs only on Windows."""
        code = "\n".join(l.split("#", 1)[0] for l in self.src.split("\n"))
        held = code.find("if (-not $d2rAlive) {\n      Write-Stage 'held'")
        # #255 (v3881, REG-3377) - the virtual-desktop grab is GONE: with D2R alive and no window pinned, only a monitor a
        # D2R window covers whole is grabbed (test_windows_films_the_game_not_the_desktop pins that rule)
        grab = code.find("Write-Stage 'monitor'")
        self.assertGreater(held, -1, "no held-eye branch: auto films the desktop when nothing pins")
        self.assertGreater(grab, -1, "the no-pin branch no longer asks for D2R's own monitor")
        self.assertLess(held, grab, "the held branch comes after the monitor grab, so it never runs first")
        self.assertNotIn("full screen (no D2R)", code, "the desktop is still filmed with no D2R alive")
        self.assertNotIn("[TvdCap]::GrabVirtual", code, "the whole virtual desktop is grabbed again")

    def test_windows_names_a_streaming_window_that_does_not_name_the_game(self):
        code = "\n".join(l.split("//", 1)[0] for l in self.src.split("\n"))
        self.assertIn('NearMiss.Add(proc + " \'" + (title.Length > 60 ? title.Substring(0, 60) : title) + "\'");', code,
                      "a streaming window without the game in its title is dropped silently on Windows")

    def test_windows_powershell_can_still_read_it(self):
        """Windows PowerShell reads a file with no BOM as ANSI, so non-ASCII there is mangled. The
        file carries em-dashes in comments and a UTF-8 BOM; it must keep one of the two properties."""
        raw = io.open(os.path.join(HERE, "capture_win.ps1"), "rb").read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf") or all(b < 128 for b in raw),
                        "capture_win.ps1 has non-ASCII and no BOM: Windows PowerShell reads it as ANSI")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "the second eye on 757518cc - Windows auto films the whole desktop again when nothing pins and no D2R runs",
        "file": "capture_win.ps1",
        "find": "    if (-not $d2rAlive) {\n      Write-Stage 'held'\n",
        "replace": "    if ($false) {\n      Write-Stage 'held'\n",
        "matches": 1,
    },
    {
        "why": "the second eye on 757518cc - a streaming window without the game in its title is dropped silently on Windows",
        "file": "capture_win.ps1",
        "find": "            if (svc && NearMiss.Count < 6) NearMiss.Add(proc + \" '\" + (title.Length > 60 ? title.Substring(0, 60) : title) + \"'\");\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#232 - substring game words again: 'GeForce NOW - Resurrected' / 'Diablo 2024' / 'd2races' pin as the game",
        "file": "tv_diablo.py",
        "find": "_GAME_RX = re.compile(r\"\\bdiablo\\s*(?:ii|2)\\b|\\bd2r\\b\")\n",
        "replace": "_GAME_RX = re.compile(r\"diablo|d2r|resurrected\")\n",
        "matches": 1,
    },
    {
        "why": "#232 - a browser by prefix again: 'Archive Utility' is an Arc tab and pins a cloud title",
        "file": "tv_diablo.py",
        "find": "    browser = any(ol == b or ol.startswith(b + \" \") for b in _BROWSER_OWNERS)\n",
        "replace": "    browser = any(ol.startswith(b) for b in _BROWSER_OWNERS)\n",
        "matches": 1,
    },
    {
        "why": "#232 - a title naming two services pins as whichever is listed first",
        "file": "tv_diablo.py",
        "find": "    if len(full) == 1:\n        return full[0]\n",
        "replace": "    if full:\n        return full[0]\n",
        "matches": 1,
    },
    {
        "why": "#232 - the scorer judges an un-normalized title: CrossOver 'Diablo(R) II' is the game to game_route and refused by the scorer",
        "file": "tv_diablo.py",
        "find": "    tl = _norm_title(title)\n    ww, hh = int(width or 0), int(height or 0)\n",
        "replace": "    tl = (title or \"\").strip().lower()\n    ww, hh = int(width or 0), int(height or 0)\n",
        "matches": 1,
    },
    {
        "why": "#232 - a cloud window naming the game that the scorer refused is dropped with the generic why again",
        "file": "tv_diablo.py",
        "find": "                elif _nr in (\"geforce-now\", \"boosteroid\"):\n",
        "replace": "                elif False:\n",
        "matches": 1,
    },
    {
        "why": "#232 - Linux reaches for Quartz again instead of saying there is nothing to pin there",
        "file": "tv_diablo.py",
        "find": "    if sys.platform.startswith(\"linux\"):\n        _PICK_WHY = (\"Linux: D2R and its cloud routes",
        "replace": "    if False:\n        _PICK_WHY = (\"Linux: D2R and its cloud routes",
        "matches": 1,
    },
    {
        "why": "#232 - every browser is blocked again: a GeForce NOW / Boosteroid tab streaming D2R can never pin",
        "file": "tv_diablo.py",
        "find": "        if not (_title_is_game or _cloud):\n",
        "replace": "        if not _title_is_game:\n",
        "matches": 1,
    },
    {
        "why": "#232 - a browser tab qualifies on the service alone: the GeForce NOW library page pins as the game",
        "file": "tv_diablo.py",
        # re-anchored (second eye on v3496): the route loop collects full/near matches now
        # re-anchored 2026-09-27: a native app's measured bare title also counts (_NATIVE_BARE_TITLES)
        "find": "            (full if (has_game or bare) else near).append(route)\n",
        "replace": "            full.append(route)\n",
        "matches": 1,
    },
    {
        "why": "#232 - the Windows finder takes any browser/cloud window, named game or not",
        "file": "capture_win.ps1",
        "find": "          if (route == \"\") {                        // a service window that does not name the game\n",
        "replace": "          if (false) {\n",
        "matches": 1,
    },
]
