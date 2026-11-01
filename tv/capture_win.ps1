# TV DIABLO - Windows capture loop (v1423)
# Zero installs: .NET System.Drawing. Read-only screenshots only.
#
#   TV_CAPTURE=auto|full|window   (default AUTO - pin D2R.exe when present, else full)
#   TV_CAPTURE_MS=350
#
# Writes:
#   frames/live.bmp, live.png (every 5th), eye.jpg, cap_target.json
#   frames/win_pin_debug.json, capture_heartbeat.txt, capture_stage.txt
#
# v1418: Pure C# Find+PrintWindow (no PowerShell EnumWindows callbacks - those hang under D2R).
#         Always write eye.jpg when we have pixels. Never BitBlt (desktop z-order lie).
# v1421: Promote frames with File.Copy(overwrite) so agent locks no longer kill film.
# v1422: Light capture under D2R - eye first, PNG rare, 350ms poll, unique tmp names.
# v1423: Per-monitor DPI awareness - 150% displays were 1920x1080 physical but capture
#         used 1280x720 logical coords = TOP-LEFT CROP only (Konyo screenshot proof).
# v1434: Smooth — eye always (800px q72); live.bmp every 2nd; PNG every 8th; 400ms poll.
# Pure ASCII + BOM for Hebrew PowerShell 5.1.

# v1423 - declare DPI awareness BEFORE any window measure / System.Drawing call.
# Without this, GetWindowRect returns logical 1280x720 on a 1920x1080@150% screen and
# PrintWindow only paints the top-left third of the real D2R framebuffer into the film.
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class TvdDpi {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int value);
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
  // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
  public static void Arm() {
    try {
      if (SetProcessDpiAwarenessContext((IntPtr)(-4))) return;
    } catch {}
    try {
      if (SetProcessDpiAwareness(2) == 0) return; // PROCESS_PER_MONITOR_DPI_AWARE
    } catch {}
    try { SetProcessDPIAware(); } catch {}
  }
}
"@
[TvdDpi]::Arm()

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -ReferencedAssemblies System.Drawing,System.Windows.Forms -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

public static class TvdCap {
  public struct RECT { public int Left, Top, Right, Bottom; }
  public struct POINT { public int X, Y; }
  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);

  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")] static extern bool IsIconic(IntPtr hWnd);
  [DllImport("user32.dll")] static extern bool IsWindow(IntPtr hWnd);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);
  [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] static extern uint GetDpiForWindow(IntPtr hWnd);
  [DllImport("gdi32.dll")] static extern int GetDeviceCaps(IntPtr hdc, int nIndex);
  [DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr hWnd);
  [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

  public class Hit {
    public IntPtr Hwnd;
    public int Left, Top, W, H;
    public string Title;
    public string Proc;
    public string Route;
    public int Score;
    public bool IsFg;
    public int Dpi;
  }

  static readonly string[] ProcNames = new string[] { "D2R", "DiabloIIResurrected", "DiabloII" };
  // #232 - HIS ORDER, 2026-09-24: the eye targets D2R however he runs it - locally (D2R.exe) OR streamed
  // from GeForce NOW / Boosteroid, in their own app or in a browser tab. Before this only D2R-process
  // windows were candidates, so a streamed session fell through to FULL SCREEN and filmed the desktop.
  // A browser qualifies ONLY with the service's name AND the game's name in its title (a guide tab
  // must never pin). The real cloud titles are UNMEASURED until his first streamed session is read.
  static readonly string[] CloudApps = new string[] { "GeForceNOW", "Boosteroid" };
  static readonly string[] Browsers = new string[] { "chrome", "msedge", "firefox", "brave", "opera", "vivaldi" };
  static readonly string[] GameWords = new string[] { "diablo ii", "diablo 2", "d2r" };
  // #232 - the second eye on v3496: substring game words pinned "GeForce NOW - Resurrected", "Diablo 2024"
  // and "d2races" as the game. A game word is a WORD now, and "resurrected" alone proves nothing. Mirrors
  // tv_diablo._GAME_RX exactly.
  static readonly System.Text.RegularExpressions.Regex GameRx =
      new System.Text.RegularExpressions.Regex(@"\bdiablo\s*(?:ii|2)\b|\bd2r\b");

  public static string NormTitle(string t) {
    t = (t ?? "").ToLowerInvariant().Replace("\u00ae", "").Replace("\u2122", "").Replace("\u00a9", "");
    return System.Text.RegularExpressions.Regex.Replace(t, @"\s+", " ").Trim();
  }

  static bool HasGame(string tl) {
    return GameRx.IsMatch(tl);
  }

  // 2026-09-27 - MEASURED on his ALT (this script's own held eye, frames/cap_target.json, 2026-09-25):
  // "a cloud window is open but its title does not name the game: Boosteroid 'Boosteroid'". Boosteroid's own
  // app titles its window with the service's name and nothing else while a game streams, so this eye held for
  // every session on that PC. A NATIVE app window whose whole title is exactly one of these pins; a browser
  // tab never does (a tab titled "Boosteroid" is their website). Mirrors tv_diablo._NATIVE_BARE_TITLES.
  static readonly string[] BoosteroidBareTitles = new string[] { "boosteroid" };

  // -> "geforce-now" | "boosteroid" | "" for a cloud-app or browser window; pure, testable
  public static string CloudRoute(string proc, string title, bool browser) {
    string pl = (proc ?? "").ToLowerInvariant();
    string tl = NormTitle(title);
    if (!browser && pl.Contains("boosteroid") && Array.IndexOf(BoosteroidBareTitles, tl) >= 0) return "boosteroid";
    if (!HasGame(tl)) return "";
    if (!browser) {
      if (pl.Contains("geforce")) return "geforce-now";
      if (pl.Contains("boosteroid")) return "boosteroid";
      return "";
    }
    bool gfn = tl.Contains("geforce now") || tl.Contains("geforcenow");
    bool bst = tl.Contains("boosteroid");
    if (gfn && bst) return "";   // names TWO services: which one streams is unknown - never pinned
    if (gfn) return "geforce-now";
    if (bst) return "boosteroid";
    return "";
  }

  public static string DpiInfo() {
    try {
      IntPtr hdc = GetDC(IntPtr.Zero);
      int logical = GetDeviceCaps(hdc, 8);   // HORZRES
      int physical = GetDeviceCaps(hdc, 118); // DESKTOPHORZRES
      ReleaseDC(IntPtr.Zero, hdc);
      return "logical=" + logical + " physical=" + physical;
    } catch { return "dpi=?"; }
  }

  // #232 - the second eye on 757518cc: a streaming window whose title does not name the game was dropped
  // SILENTLY here (the Mac names it as a near-miss). Collected per scan, reported by the held eye.
  public static List<string> NearMiss = new List<string>();

  public static List<Hit> FindD2R() {
    NearMiss = new List<string>();
    var want = new HashSet<int>();
    var names = new Dictionary<int, string>();
    var kind = new Dictionary<int, string>();   // #232 - "local" | "cloud" | "browser"
    foreach (var n in ProcNames) {
      try {
        foreach (var p in Process.GetProcessesByName(n)) {
          want.Add(p.Id);
          names[p.Id] = p.ProcessName;
          kind[p.Id] = "local";
          try { p.Dispose(); } catch {}
        }
      } catch {}
    }
    foreach (var n in CloudApps) {
      try {
        foreach (var p in Process.GetProcessesByName(n)) {
          want.Add(p.Id); names[p.Id] = p.ProcessName; kind[p.Id] = "cloud";
          try { p.Dispose(); } catch {}
        }
      } catch {}
    }
    foreach (var n in Browsers) {
      try {
        foreach (var p in Process.GetProcessesByName(n)) {
          want.Add(p.Id); names[p.Id] = p.ProcessName; kind[p.Id] = "browser";
          try { p.Dispose(); } catch {}
        }
      } catch {}
    }
    var hits = new List<Hit>();
    if (want.Count == 0) return hits;
    IntPtr fg = GetForegroundWindow();
    EnumWindows((h, lp) => {
      try {
        if (!IsWindow(h) || IsIconic(h)) return true;
        uint pidU = 0;
        GetWindowThreadProcessId(h, out pidU);
        int pid = (int)pidU;
        if (!want.Contains(pid)) return true;
        RECT wr;
        if (!GetWindowRect(h, out wr)) return true;
        int left = wr.Left, top = wr.Top;
        int w = wr.Right - wr.Left, hh = wr.Bottom - wr.Top;
        RECT cr;
        if (GetClientRect(h, out cr)) {
          int cw = cr.Right - cr.Left, ch = cr.Bottom - cr.Top;
          if (cw >= 320 && ch >= 240) {
            POINT pt; pt.X = 0; pt.Y = 0;
            if (ClientToScreen(h, ref pt)) { left = pt.X; top = pt.Y; w = cw; hh = ch; }
          }
        }
        // v1423 - after DPI-aware arm, W/H are PHYSICAL pixels. Reject tiny tools only.
        if (w < 640 || hh < 400) return true;
        var sb = new StringBuilder(512);
        GetWindowText(h, sb, 512);
        string title = sb.ToString() ?? "";
        string tl = title.ToLowerInvariant();
        if (tl.Contains("battle.net") || tl.Contains("tv diablo") || tl.Contains("farming bible")) return true;
        string proc = names.ContainsKey(pid) ? names[pid] : "D2R";
        string k = kind.ContainsKey(pid) ? kind[pid] : "local";
        string route = "local";
        if (k != "local") {
          route = CloudRoute(proc, title, k == "browser");
          if (route == "") {                        // a service window that does not name the game
            bool svc = (k == "cloud") || tl.Contains("geforce now") || tl.Contains("geforcenow") || tl.Contains("boosteroid");
            if (svc && NearMiss.Count < 6) NearMiss.Add(proc + " '" + (title.Length > 60 ? title.Substring(0, 60) : title) + "'");
            return true;
          }
        }
        bool isFg = (h == fg);
        int score = (route == "local" ? 8000 : 7000) + (isFg ? 500 : 0);
        if (tl.Contains("resurrected") || tl.Contains("diablo ii")) score += 1500;
        // Prefer the largest window (true fullscreen game over tiny helper hwnds).
        score += Math.Min((w * hh) / 80000, 200);
        int dpi = 0;
        try { dpi = (int)GetDpiForWindow(h); } catch { dpi = 0; }
        if (dpi < 72) dpi = 0;
        hits.Add(new Hit {
          Hwnd = h, Left = left, Top = top, W = w, H = hh,
          Title = title, Proc = proc, Route = route, Score = score, IsFg = isFg, Dpi = dpi
        });
      } catch {}
      return true;
    }, IntPtr.Zero);
    hits.Sort((a, b) => b.Score.CompareTo(a.Score));
    return hits;
  }

  public static bool D2RProcessAlive() {
    foreach (var n in ProcNames) {
      try {
        var ps = Process.GetProcessesByName(n);
        if (ps != null && ps.Length > 0) {
          foreach (var p in ps) try { p.Dispose(); } catch {}
          return true;
        }
      } catch {}
    }
    return false;
  }

  public static string Grab(Hit hit, string framesDir) {
    if (hit == null || hit.Hwnd == IntPtr.Zero || hit.W < 32 || hit.H < 32) return null;
    // v1423 - re-measure EVERY grab in physical pixels (window may move / DPI path may
    // have been wrong at find-time). Prefer FULL window rect for PrintWindow so chrome
    // + client land 1:1; fall back to stored client size.
    int left = hit.Left, top = hit.Top, bw = hit.W, bh = hit.H;
    try {
      RECT wr;
      if (GetWindowRect(hit.Hwnd, out wr)) {
        int ww = wr.Right - wr.Left, wh = wr.Bottom - wr.Top;
        if (ww >= 640 && wh >= 400) { left = wr.Left; top = wr.Top; bw = ww; bh = wh; }
      }
      RECT cr;
      if (GetClientRect(hit.Hwnd, out cr)) {
        int cw = cr.Right - cr.Left, ch = cr.Bottom - cr.Top;
        // Borderless: client ~= window. Windowed: prefer client (no title bar in film).
        if (cw >= 640 && ch >= 400 && cw * ch >= (int)(bw * bh * 0.85)) {
          POINT pt; pt.X = 0; pt.Y = 0;
          if (ClientToScreen(hit.Hwnd, ref pt)) {
            left = pt.X; top = pt.Y; bw = cw; bh = ch;
          }
        }
      }
    } catch {}
    hit.Left = left; hit.Top = top; hit.W = bw; hit.H = bh;

    Bitmap bmp = null;
    Graphics g = null;
    string how = null;
    try {
      bmp = new Bitmap(bw, bh);
      g = Graphics.FromImage(bmp);
      IntPtr hdc = g.GetHdc();
      try {
        // 2 = PW_RENDERFULLCONTENT (DWM composition / DirectX games)
        bool ok = PrintWindow(hit.Hwnd, hdc, 2);
        if (!ok) PrintWindow(hit.Hwnd, hdc, 0);
      } finally {
        g.ReleaseHdc(hdc);
      }
      if (!MostlyBlack(bmp)) {
        how = "PrintWindow";
      } else {
        // Foreground CopyFromScreen uses PHYSICAL coords after DPI arm.
        if (GetForegroundWindow() == hit.Hwnd) {
          g.CopyFromScreen(left, top, 0, 0, new Size(bw, bh));
          if (!MostlyBlack(bmp)) how = "CopyFromScreen-fg";
        }
      }
      if (how == null) return null;
      SaveAll(bmp, framesDir);
      return how;
    } catch {
      return null;
    } finally {
      try { if (g != null) g.Dispose(); } catch {}
      try { if (bmp != null) bmp.Dispose(); } catch {}
    }
  }

  public static void GrabPrimary(string framesDir) {
    var b = System.Windows.Forms.Screen.PrimaryScreen.Bounds;
    using (var bmp = new Bitmap(b.Width, b.Height))
    using (var g = Graphics.FromImage(bmp)) {
      g.CopyFromScreen(b.X, b.Y, 0, 0, bmp.Size);
      SaveAll(bmp, framesDir);
    }
  }

  public static void GrabVirtual(string framesDir) {
    var b = System.Windows.Forms.SystemInformation.VirtualScreen;
    using (var bmp = new Bitmap(b.Width, b.Height))
    using (var g = Graphics.FromImage(bmp)) {
      g.CopyFromScreen(b.Left, b.Top, 0, 0, bmp.Size);
      SaveAll(bmp, framesDir);
    }
  }

  static bool MostlyBlack(Bitmap bmp) {
    try {
      int[] xs = new int[] { bmp.Width/2, bmp.Width/4, 3*bmp.Width/4, bmp.Width/4, 3*bmp.Width/4 };
      int[] ys = new int[] { bmp.Height/2, bmp.Height/4, bmp.Height/4, 3*bmp.Height/4, 3*bmp.Height/4 };
      int dark = 0;
      for (int i = 0; i < 5; i++) {
        Color c = bmp.GetPixel(xs[i], ys[i]);
        if (c.R < 12 && c.G < 12 && c.B < 12) dark++;
      }
      return dark >= 4;
    } catch { return true; }
  }

  // v1421 — promote via Copy(overwrite) not Delete+Move. Under ON AIR the agent holds
  // live.bmp / eye.jpg for freezes; Delete fails, Move throws "file already exists",
  // and film stalls (eyeAge 7s+) with primary/virtual fail spam in the log.
  // v1422 — unique tmp names (GUID) so a killed mid-write never leaves a sticky .tmp that
  // blocks the next Save. Eye first (film), then BMP (agent), PNG rare (CPU killer under D2R).
  static int _saveN = 0;

  static void Promote(string tmp, string finalPath) {
    try {
      File.Copy(tmp, finalPath, true);
    } catch {
      try {
        if (File.Exists(finalPath)) File.Delete(finalPath);
        File.Move(tmp, finalPath);
        return;
      } catch { return; }
    }
    try { File.Delete(tmp); } catch {}
  }

  static string TmpPath(string framesDir, string tag, string ext) {
    return Path.Combine(framesDir, "._tvd_" + tag + "_" + Guid.NewGuid().ToString("N").Substring(0, 8) + ext);
  }

  static void SaveAll(Bitmap bmp, string framesDir) {
    _saveN++;
    string liveBmp = Path.Combine(framesDir, "live.bmp");
    string livePng = Path.Combine(framesDir, "live.png");
    string eyeJpg = Path.Combine(framesDir, "eye.jpg");

    // 1) EYE FIRST — console film. v1434: cap 800px + Encoder quality 72 (was full JPEG default).
    // At 1920x1080 source this is the main UX surface; keep it cheap and always fresh.
    int maxPx = 800;
    int nw = bmp.Width, nh = bmp.Height;
    if (nw > maxPx || nh > maxPx) {
      double scale = Math.Min(maxPx / (double)nw, maxPx / (double)nh);
      nw = Math.Max(1, (int)(bmp.Width * scale));
      nh = Math.Max(1, (int)(bmp.Height * scale));
    }
    string tmpEye = TmpPath(framesDir, "eye", ".jpg");
    using (var eye = new Bitmap(nw, nh))
    using (var eg = Graphics.FromImage(eye)) {
      eg.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Bilinear;
      eg.DrawImage(bmp, 0, 0, nw, nh);
      try {
        var codec = System.Array.Find(
          ImageCodecInfo.GetImageEncoders(),
          c => c.MimeType == "image/jpeg");
        if (codec != null) {
          var ep = new EncoderParameters(1);
          ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 72L);
          eye.Save(tmpEye, codec, ep);
        } else {
          eye.Save(tmpEye, ImageFormat.Jpeg);
        }
      } catch {
        eye.Save(tmpEye, ImageFormat.Jpeg);
      }
    }
    Promote(tmpEye, eyeJpg);

    // 2) live.bmp — agent settle/intelligence. v1434: ONLY every 2nd frame.
    // Full 1920x1080 BMP is ~8MB; writing every tick was the #1 lag after PNG death.
    // Agent POLL is ~1.8s so every-other @350ms still refreshes ~1.4fps for settle.
    if ((_saveN % 2) == 0) {
      string tmpBmp = TmpPath(framesDir, "bmp", ".bmp");
      bmp.Save(tmpBmp, ImageFormat.Bmp);
      Promote(tmpBmp, liveBmp);
    }

    // 3) live.png — every 8th only (was 5th). Soft fallback for vision convert path.
    if ((_saveN % 8) == 0) {
      string tmpPng = TmpPath(framesDir, "png", ".png");
      try {
        bmp.Save(tmpPng, ImageFormat.Png);
        Promote(tmpPng, livePng);
      } catch {
        try { if (File.Exists(tmpPng)) File.Delete(tmpPng); } catch {}
      }
    }
  }
}
"@

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$frames = Join-Path $here 'frames'
New-Item -ItemType Directory -Force -Path $frames | Out-Null
# scrub sticky temps from prior crash
Get-ChildItem -LiteralPath $frames -Filter '._tvd_*' -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath $frames -Filter '*.tmp' -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$mode = if ($env:TV_CAPTURE) { $env:TV_CAPTURE.ToLower().Trim() } else { 'auto' }
# v1434 — default 400ms. Eye always fresh; BMP half-rate. Smoother under 1920x1080 + D2R.
$pollMs = 400
if ($env:TV_CAPTURE_MS) {
  try { $pollMs = [Math]::Max(150, [int]$env:TV_CAPTURE_MS) } catch { $pollMs = 400 }
}

function Write-Stage([string]$s) {
  try { Set-Content -LiteralPath (Join-Path $frames 'capture_stage.txt') -Value $s -Encoding UTF8 } catch {}
}

function Write-CapTarget([string]$mode, [string]$label, $hit) {
  $p = Join-Path $frames 'cap_target.json'
  $alive = $false
  try { $alive = [TvdCap]::D2RProcessAlive() } catch {}
  $obj = @{
    mode = $mode
    label = $label
    ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    d2rProcess = $alive
  }
  # The pin already measured the route, the window title, the client size and the DPI.
  # Those fields are what a sealed reel copies. The label string stays as it was: the
  # console still reads the route out of it. A DPI the API did not return stays absent.
  if ($null -ne $hit) {
    $route = [string]$hit.Route
    if ($route -eq 'local' -or $route -eq 'crossover') { $route = 'native' }
    if ($route -eq 'native' -or $route -eq 'geforce-now' -or $route -eq 'boosteroid' -or $route -eq 'unknown') {
      $obj.route = $route
    }
    $title = ([string]$hit.Title).Trim()
    if ($title.Length -gt 0) { $obj.windowLabel = $title }
    $ww = 0; $hh = 0
    try { $ww = [int]$hit.W; $hh = [int]$hit.H } catch { $ww = 0; $hh = 0 }
    if ($ww -gt 0 -and $hh -gt 0) { $obj.w = $ww; $obj.h = $hh }
    $dpi = 0
    try { $dpi = [int]$hit.Dpi } catch { $dpi = 0 }
    if ($dpi -ge 72) { $obj.dpi = $dpi; $obj.dpiMeasured = $true }
  }
  # v1419: UTF-8 WITHOUT BOM — agent json.load('utf-8') used to miss pin when BOM present
  $json = ($obj | ConvertTo-Json -Compress)
  $utf8NoBom = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($p, $json, $utf8NoBom)
  try {
    [System.IO.File]::WriteAllText((Join-Path $frames 'cap_target.txt'), "$mode|$label", $utf8NoBom)
  } catch {}
}

function Write-PinDebug($hits) {
  try {
    $debug = @()
    foreach ($h in $hits) {
      $debug += @{
        proc = $h.Proc; route = $h.Route; title = $h.Title; score = $h.Score
        w = $h.W; h = $h.H; left = $h.Left; top = $h.Top
        dpi = $h.Dpi
      }
    }
    $best = $null
    if ($hits -and $hits.Count -gt 0) { $best = ($hits[0].Proc + ' - ' + $hits[0].Title) }
    $dpiInfo = ''
    try { $dpiInfo = [TvdCap]::DpiInfo() } catch {}
    $obj = @{
      ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
      d2rProcessAlive = [TvdCap]::D2RProcessAlive()
      candidateCount = @($hits).Count
      best = $best
      dpi = $dpiInfo
      candidates = $debug
    }
    ($obj | ConvertTo-Json -Depth 5 -Compress) | Set-Content -LiteralPath (Join-Path $frames 'win_pin_debug.json') -Encoding UTF8
  } catch {}
}

Write-Host ("TV DIABLO capture (Windows) mode=$mode poll=${pollMs}ms v1434 smooth eye-always BMP/2 PNG/8")
try { Write-Host ("  dpi: " + [TvdCap]::DpiInfo()) } catch {}
# v1441 — BelowNormal so game + control UI stay responsive while we PrintWindow.
try {
  $p = Get-Process -Id $PID -ErrorAction SilentlyContinue
  if ($p) { $p.PriorityClass = 'BelowNormal' }
} catch {}
$lastLabel = ''
$loopN = 0
# #236 - the second eye on 298de387: TV_CAPTURE=off was not a stop here. 'off' matched neither 'full' nor
# window/win/game, so the loop still found, grabbed and fell through to the whole desktop. Off means this
# console never reads the screen: say so once and leave.
if ($mode -eq 'off' -or $mode -eq 'none') {
  Write-CapTarget 'off' 'capture is OFF (TV_CAPTURE) - this console never reads the screen'
  Write-Host '  capture is OFF (TV_CAPTURE) - not reading the screen'
  exit 0
}

# REG-1502 - ONE CAPTURE PER CONSOLE, ENFORCED BY THE CAPTURE ITSELF. MEASURED 2026-09-29 on the ALT: FIVE of these
# ran at once - four children of one console (started 10:23, 10:44, 14:31, 14:42) and one from the day before -
# each PrintWindow-ing his Boosteroid window every 400 ms. dwm.exe died of memory exhaustion (0xc00001ad) eight
# times in an hour and took Boosteroid with it. The console's stop is a taskkill whose result nobody read, so a kill
# that did not land left a capture nobody remembered. So the script no longer trusts anyone to stop it: the console's
# pid file is its LEASE. It leaves when the lease is withdrawn (stop) or handed to another pid (a newer capture).
# v3850 (Elad 18:03 2026-10-31) — the console that started it exiting is not a reason to leave. One recorder
# is kept by control_capture.lease (Get-RecorderLeaseVerdict). A crash no longer stops the film.
$leasePath = Join-Path $here 'control_capture.pid'
$consolePid = 0
try { if ($env:TV_CONSOLE_PID) { $consolePid = [int]$env:TV_CONSOLE_PID } } catch { $consolePid = 0 }
$bornAt = [DateTime]::UtcNow
# REG-1509 - this capture's own start, for the pid-reuse test below. $null when it cannot be read (the test is skipped).
$myStart = $null
try { $myStart = (Get-Process -Id $PID -ErrorAction Stop).StartTime } catch { $myStart = $null }
function Get-LeaseVerdict([string]$leaseFile, [int]$myPid, [int]$parentPid, [double]$ageS, [double]$graceS, $myStart = $null) {
  # -> $null to keep filming, or the reason to leave. UNKNOWN (an unreadable lease) is never a reason to leave.
  # v3850 (Elad 18:03 2026-10-31) - the console that started me being gone is NO LONGER a reason to leave: the
  # recorder outlives its console. One recorder is kept by control_capture.lease instead (Get-RecorderLeaseVerdict).
  if ($ageS -lt $graceS) { return $null }      # the console writes the lease just after it spawns us
  if (-not (Test-Path -LiteralPath $leaseFile)) { return 'the console withdrew my lease (it stopped the capture)' }
  $raw = $null
  try { $raw = ([System.IO.File]::ReadAllText($leaseFile)).Trim() } catch { return $null }
  $holder = 0
  if (-not [int]::TryParse($raw, [ref]$holder)) { return $null }
  if ($holder -ne $myPid) { return "a newer capture holds the lease (pid $holder)" }
  return $null
}

# v3850 - THE ONE-RECORDER LEASE (recorder_lease.py is the Python half; the constants are pinned equal by a law).
$recLeasePath = Join-Path $here 'control_capture.lease'
$RecLeaseRenewS = 30
$RecLeaseStaleS = 90
function Get-RecorderLeaseVerdict([string]$text, [int]$myPid, [int64]$nowMs) {
  # -> 'hold' (mine) | 'refuse' (another live, fresh recorder holds it) | 'take' (free, stale, or its pid is dead)
  if (-not $text) { return 'take' }
  $m = [regex]::Match($text, 'pid=(\d+)\s+t=(\d+)')
  if (-not $m.Success) { return 'take' }
  $hp = [int]$m.Groups[1].Value
  $ht = [int64]$m.Groups[2].Value
  if ($myPid -gt 0 -and $hp -eq $myPid) { return 'hold' }
  $age = $nowMs - $ht
  if ($age -ge 0 -and $age -le ($RecLeaseStaleS * 1000)) {
    if (Get-Process -Id $hp -ErrorAction SilentlyContinue) { return 'refuse' }
  }
  return 'take'
}
function Read-RecLease { try { return [System.IO.File]::ReadAllText($recLeasePath) } catch { return $null } }
function Write-RecLease { try { [System.IO.File]::WriteAllText($recLeasePath, ("pid={0} t={1}" -f $PID, [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())) } catch {} }
if ($env:TV_REC_LEASE_SELFTEST -ne '1') {
  $v0 = Get-RecorderLeaseVerdict (Read-RecLease) $PID ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
  if ($v0 -eq 'refuse') {
    Write-Host '  capture leaving at start: a live recorder already holds control_capture.lease (one recorder only)'
    exit 0
  }
  Write-RecLease
}
$recRenewAt = [DateTime]::UtcNow.AddSeconds($RecLeaseRenewS)

while ($true) {
  $loopN++
  if ([DateTime]::UtcNow -ge $recRenewAt) {
    $recRenewAt = [DateTime]::UtcNow.AddSeconds($RecLeaseRenewS)
    if ((Get-RecorderLeaseVerdict (Read-RecLease) $PID ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())) -eq 'refuse') {
      Write-Host ("  capture pid $PID leaving: another live recorder holds the lease")
      Write-Stage 'left:another recorder holds the lease'
      exit 0
    }
    Write-RecLease
  }
  if (($loopN % 5) -eq 1) {
    $why = Get-LeaseVerdict $leasePath $PID $consolePid (([DateTime]::UtcNow - $bornAt).TotalSeconds) 15 $myStart
    if ($why) {
      Write-Host ("  capture pid $PID leaving: " + $why)
      Write-Stage ("left:" + $why)
      if ((Get-RecorderLeaseVerdict (Read-RecLease) $PID ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())) -eq 'hold') {
        try { Remove-Item -LiteralPath $recLeasePath -Force -ErrorAction SilentlyContinue } catch {}
      }
      exit 0
    }
  }
  try {
    Set-Content -LiteralPath (Join-Path $frames 'capture_heartbeat.txt') -Value ("n={0} t={1}" -f $loopN, [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) -Encoding UTF8
  } catch {}
  try {
    Write-Stage 'find'
    $d2rAlive = $false
    try { $d2rAlive = [TvdCap]::D2RProcessAlive() } catch {}
    $hits = @()
    $best = $null
    if ($mode -ne 'full') {
      try { $hits = [TvdCap]::FindD2R() } catch { Write-Host "  find err: $_" }
      Write-PinDebug $hits
      if ($hits -and $hits.Count -gt 0) { $best = $hits[0] }
    }

    if ($best -and $mode -ne 'full') {
      Write-Stage 'grab'
      if ($best.Title -ne $lastLabel) {
        Write-Host ("  eye pinned: {0} - {1} ({2}x{3})" -f $best.Proc, $best.Title, $best.W, $best.H)
        $lastLabel = $best.Title
      }
      $how = $null
      try { $how = [TvdCap]::Grab($best, $frames) } catch { Write-Host "  grab err: $_" }
      # heartbeat after grab so a hung Save is visible in capture_stage + stale hb
      try {
        Set-Content -LiteralPath (Join-Path $frames 'capture_heartbeat.txt') -Value ("n={0} t={1} postgrab" -f $loopN, [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) -Encoding UTF8
      } catch {}
      if ($how) {
        Write-Stage ("ok:" + $how)
        Write-CapTarget 'window' ("{0} [{1}] - {2} via {3}" -f $best.Proc, $best.Route, $best.Title, $how) $best
        Start-Sleep -Milliseconds $pollMs
        continue
      }
      if ($best.IsFg) {
        Write-Stage 'primary-fg'
        try {
          [TvdCap]::GrabPrimary($frames)
          Write-CapTarget 'window' 'D2R foreground - primary monitor'
          Start-Sleep -Milliseconds $pollMs
          continue
        } catch { Write-Host "  primary fail: $_" }
      } else {
        Write-Stage 'need-focus'
        if ($lastLabel -ne '__need_focus__') {
          Write-Host '  D2R pin found but grab black and not focused - click GAME window'
          $lastLabel = '__need_focus__'
        }
        Write-CapTarget 'waiting' 'D2R running - click Diablo window (PrintWindow black; not filming chat)'
        Start-Sleep -Milliseconds 400
        continue
      }
    }

    if ($mode -eq 'window' -or $mode -eq 'win' -or $mode -eq 'game') {
      Write-Stage 'waiting-d2r'
      $msg = if ($d2rAlive) {
        'D2R.exe running but no capturable window - try borderless windowed'
      } else {
        'D2R.exe not found - open Diablo II Resurrected in-game (not only Battle.net)'
      }
      Write-CapTarget 'waiting' $msg
      Start-Sleep -Milliseconds 500
      continue
    }

    # #232 - the second eye on 757518cc: auto filmed the WHOLE DESKTOP whenever nothing pinned, even with no
    # D2R running at all (a streamed session whose title lacked a game word, a browser tab). The Mac holds the
    # eye (v1251); Windows now does too, unless a LOCAL D2R is alive (the exclusive-fullscreen case).
    if (-not $d2rAlive) {
      Write-Stage 'held'
      $nm = @()
      try { $nm = @([TvdCap]::NearMiss) } catch {}
      $msg = 'eye held - no game window and no D2R.exe, so the desktop is never filmed'
      if ($nm.Count -gt 0) { $msg += '; a cloud window is open but its title does not name the game: ' + (($nm | Select-Object -First 3) -join '; ') }
      if ($lastLabel -ne '__held__') { Write-Host ('  ' + $msg); $lastLabel = '__held__' }
      Write-CapTarget 'waiting' $msg
      Start-Sleep -Milliseconds 500
      continue
    }
    Write-Stage 'virtual'
    if ($lastLabel -ne '__full__') {
      Write-Host '  full virtual screen (no D2R pin)'
      $lastLabel = '__full__'
    }
    try {
      [TvdCap]::GrabVirtual($frames)
      Write-CapTarget 'window' 'D2R alive - full virtual fallback'
    } catch {
      Write-Host "  virtual fail: $_"
    }
  } catch {
    Write-Host "  loop err: $_"
    Write-Stage ("err:" + $_)
  }
  Start-Sleep -Milliseconds $pollMs
}
