# -*- coding: utf-8 -*-
"""#255 (v3881, REG-3377) - A WINDOWS PC FILMS THE GAME'S OWN PIXELS, AT THE MAC'S SIZE, AND NEVER ITS DESKTOP.

MEASURED 2026-11-07 on a Windows PC that plays D2R windowed (client 1507x755), and on the reader-parity bench
(tv/reader_parity.py, 48 real frames from that PC and the Mac, run on the Mac AND on a Windows PC):
  1. capture_win.ps1 PrintWindow(hwnd, hdc, 2) painted the WHOLE window - title bar and borders - into a CLIENT-sized
     bitmap: 31 of 32 sampled frames from that PC carry the Windows caption at the top and lose the bottom of the HUD, and
     every anchor the readers place is shifted (the runes crop band moved 1.4 % of the width with the caption cut).
  2. its reels archived eye.jpg - the console's 800 px / q72 thumbnail - while the Mac's reels hold 1440 px from the full
     capture: at 800 px the inventory-title eye lost 7 of 16 frames and the runes enlarge changed on 8 of 16; the Grok CLI
     read the same header "crisp" at 1440 and "soft" at 800.
  3. GrabVirtual (every monitor) ran whenever D2R.exe was alive and no window pinned, and GrabPrimary (the whole primary
     monitor) whenever the window grab came back black - on a windowed PC that is his DESKTOP around the game. One reel on
     that PC held a frame of both monitors (browsers, chat).
Now: PrintWindow takes PW_CLIENTONLY whenever the bitmap is the client size; the reel is filmed from the full frame
(live.bmp) shrunk to FILM_MAX_PX like the Mac's, the eye only a fallback; and a monitor is grabbed ONLY when the
foreground window is a D2R process covering that monitor whole - GrabVirtual and GrabPrimary no longer exist.
On Windows the capture's C# is COMPILED here (Add-Type) - a source pin alone cannot say it builds. RED_PROOF below.
[[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

PS1 = os.path.join(HERE, "capture_win.ps1")
TVD = os.path.join(HERE, "tv_diablo.py")
ADD = 'Add-Type -ReferencedAssemblies System.Drawing,System.Windows.Forms -TypeDefinition @"'


import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()   # v3881 pre-flight - its mkdtemp scratch is collected (test_a_test_run_leaves_no_scratch_dirs)
def _ps1():
    return io.open(PS1, encoding="utf-8-sig").read().replace("\r\n", "\n")


def _csharp():
    s = _ps1()
    i = s.index(ADD)
    return s[i:s.index('\n"@', i) + 3]


def _code(s):
    """the C# with its // comments stripped - prose about a removed call must not read as the call"""
    return "\n".join(l.split("//", 1)[0] for l in s.split("\n"))


class TheCaptureFilmsTheGame(unittest.TestCase):

    def test_a_client_sized_bitmap_asks_printwindow_for_the_client_only(self):
        """* THE POINT (31 of 32 windowed frames carried the caption): client size -> PW_CLIENTONLY | PW_RENDERFULLCONTENT"""
        c = _code(_csharp())
        self.assertIn("left = pt.X; top = pt.Y; bw = cw; bh = ch; clientOnly = true;", c)
        self.assertIn("uint pwf = clientOnly ? 3u : 2u;", c)
        self.assertIn("bool ok = PrintWindow(hit.Hwnd, hdc, pwf);", c)

    def test_the_desktop_grabbers_are_gone(self):
        c = _code(_csharp())
        for gone in ("GrabVirtual(", "GrabPrimary(", "SystemInformation.VirtualScreen", "PrimaryScreen.Bounds"):
            self.assertNotIn(gone, c, "%s can film the desktop again" % gone)
        loop = "\n".join(l.split("#", 1)[0] for l in _ps1().split("\n"))
        self.assertNotIn("[TvdCap]::GrabVirtual", loop)
        self.assertNotIn("[TvdCap]::GrabPrimary", loop)

    def test_a_monitor_is_filmed_only_when_d2r_covers_it(self):
        c = _code(_csharp())
        i = c.index("public static bool D2RCoversItsMonitor(out Rectangle bounds) {")
        body = c[i:c.index("\n  }\n", i)]
        self.assertIn("IntPtr fg = GetForegroundWindow();", body)
        self.assertIn("if (!isD2R) return false;", body, "a non-D2R foreground window can have its monitor filmed")
        self.assertIn("if (wr.Left <= scr.Left && wr.Top <= scr.Top && wr.Right >= scr.Right && wr.Bottom >= scr.Bottom) {", body,
                      "a D2R window that does NOT cover its monitor gets the whole monitor filmed")
        j = c.index("public static bool GrabD2RMonitor(string framesDir) {")
        self.assertIn("if (!D2RCoversItsMonitor(out b)) return false;", c[j:c.index("\n  }\n", j)])

    @unittest.skipUnless(sys.platform == "win32", "the capture's C# compiles only on Windows - UNMEASURED here; "
                                                  "GitHub's Windows runner and every Windows PC prove it")
    def test_the_capture_compiles_on_windows_and_holds_without_d2r(self):
        d = tempfile.mkdtemp(prefix="tvd_capc_")
        ps = os.path.join(d, "c.ps1")
        with io.open(ps, "w", encoding="utf-8-sig") as fh:
            fh.write("Add-Type -AssemblyName System.Drawing\nAdd-Type -AssemblyName System.Windows.Forms\n" + _csharp() + "\n"
                     "$r = [System.Drawing.Rectangle]::Empty\n"
                     "'OK ' + ([TvdCap].GetMethod('GrabVirtual') -eq $null) + ' ' + ([TvdCap].GetMethod('GrabPrimary') -eq $null)"
                     " + ' ' + [TvdCap]::D2RCoversItsMonitor([ref]$r)\n")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps], capture_output=True,
                           text=True, timeout=240, encoding="utf-8", errors="replace")
        self.assertIn("OK True True False", r.stdout, (r.stdout + r.stderr)[-1200:])


class TheReelIsFilmedAtTheMacsSize(unittest.TestCase):

    def _src(self):
        return io.open(TVD, encoding="utf-8").read()

    def test_the_windows_reel_archives_the_full_frame_first(self):
        s = self._src()
        self.assertIn('_wfull = os.path.join(FRAMES, "live.bmp")', s)
        self.assertIn('_wsrc, _wwhy = _wfull, "win-full"', s, "the Windows reel archives the 800 px thumbnail again")
        self.assertIn("_archive_footage_copy(_wsrc, _wnow, why=_wwhy)", s)

    def test_a_full_windows_frame_becomes_a_mac_sized_film_frame(self):
        """the shrink the Mac's film takes, on a BMP the size a windowed PC's full capture is"""
        from PIL import Image
        os.environ.setdefault("TV_STUB", "1")
        import tv_diablo as t
        d = tempfile.mkdtemp(prefix="tvd_film_")
        src, dest = os.path.join(d, "live.bmp"), os.path.join(d, "f_1.jpg")
        Image.new("RGB", (2560, 1440), (90, 70, 40)).save(src, "BMP")
        self.assertTrue(t._film_shrink(src, dest, t.FILM_MAX_PX, t.FILM_JPEG_Q))
        with Image.open(dest) as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.size, (t.FILM_W, t.FILM_H),
                             "a 16:9 Windows frame did not become 1920x1080: %r" % (im.size,))

    def test_the_last_good_copy_of_a_bmp_is_the_film_frame(self):
        self.assertIn('_sh.copyfile(dest if str(src_path).lower().endswith(".bmp") else src_path, last_tmp)', self._src())


RED_PROOF = [
    {"why": "REG-3377 - a windowed capture paints the whole window (caption + borders) into the client bitmap again",
     "file": "tv/capture_win.ps1", "find": "        uint pwf = clientOnly ? 3u : 2u;", "replace": "        uint pwf = 2u;",
     "matches": 1},
    {"why": "REG-3377 - any foreground window's monitor can be filmed (the process check gone)",
     "file": "tv/capture_win.ps1", "find": "    if (!isD2R) return false;\n", "replace": "\n", "matches": 1},
    {"why": "REG-3377 - a windowed D2R gets its whole monitor - his desktop - filmed",
     "file": "tv/capture_win.ps1",
     "find": "    if (wr.Left <= scr.Left && wr.Top <= scr.Top && wr.Right >= scr.Right && wr.Bottom >= scr.Bottom) {",
     "replace": "    if (true) {", "matches": 1},
    {"why": "REG-3377 - the Windows reel archives the 800 px thumbnail again",
     "file": "tv/tv_diablo.py", "find": '            _wsrc, _wwhy = _wfull, "win-full"', "replace": '            _wsrc, _wwhy = _weye, "win-eye"',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
