# TV DIABLO - Windows launcher ONLY (Desktop - native pywebview / WebView2, NOT Chrome)
# NOT for Mac. Mac uses start_tvd_mac.sh / install-tvd.sh on a different machine.
# Agent + capture stay hidden. Controls: ON/OFF/STOP/RESTART/SIM.
# Encoding: ASCII-only strings so Windows PowerShell 5.1 never mis-parses UTF-8.
#
# v1444-v1448 UX launch smooth:
#   - ready probe = /api/status (NOT full doctor ok:true which is false under ON AIR + SLOW)
#   - if already up: focus + exit BEFORE git/pip (no lag, no second window)
#   - auto-pull time-boxed; never blocks a warm relaunch
#   - C# focus (no PS EnumWindows hang under D2R)
#   - short ready wait; no error dialog while python still starting
#
# 2026-10-01 REG-1660 - his ruling: every Windows console starts at sign-in, in the BACKGROUND. -Background is the
# sign-in start: it passes --background (the console opens HIDDEN - the service runs, the Desktop icon brings the
# window), never brings a running console forward, skips the window wait, and never pops a dialog over a sign-in.
param([switch]$Background)
$ErrorActionPreference = 'Continue'
if ($env:OS -ne 'Windows_NT') {
  Write-Host 'TV DIABLO start_tvd_win.ps1 is Windows only.' -ForegroundColor Red
  return
}
$env:TV_PLATFORM = 'windows'
$env:TV_OS = 'windows'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $here
$launchLog = Join-Path $here 'start_tvd_win.log'

function Write-TvdLaunchLog([string]$msg) {
  $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  try { Add-Content -LiteralPath $launchLog -Value $line -Encoding UTF8 } catch {}
}

function Test-TvdControlUp {
  # v1444 - control is UP when /api/status answers with a ver field.
  # NEVER require doctor.ok=true: that is false while LIVE with frame faults and takes seconds.
  try {
    $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:17772/api/status' -UseBasicParsing -TimeoutSec 0.35
    $body = [string]$resp.Content
    if ($body -match '"ver"\s*:\s*"v') { return $true }
  } catch {}
  return $false
}

function Focus-TvdWindow([bool]$unhide = $true, [uint32]$wantPid = 0) {
  # v1446 - pure C# EnumWindows (PS scriptblock EnumWindows hangs under D2R load).
  # v1460 - HIDDEN windows count too. The old callback bailed on !IsWindowVisible and only
  # ever handled IsIconic, so an SW_HIDE-ed 'TV DIABLO' window was unreachable: control kept
  # answering /api/status, the launcher took its 'already up - focus and leave' branch, focus
  # silently found nothing, and every Desktop double-click did nothing at all. Now we collect
  # visible AND hidden matches, prefer visible, and SW_SHOW a hidden one before raising it.
  # Also report whether the raise actually took (Law 9) instead of always logging success.
  try {
    if (-not ('TvdFocusFast' -as [type])) {
      Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class TvdFocusFast {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  const int SW_SHOW = 5;
  const int SW_RESTORE = 9;
  static uint wantPid = 0;
  static IntPtr vis = IntPtr.Zero;
  static IntPtr hid = IntPtr.Zero;
  public static bool WasHidden = false;
  public static bool Raised = false;
  public static bool NowVisible = false;
  static bool Cb(IntPtr h, IntPtr l) {
    var sb = new StringBuilder(256);
    GetWindowText(h, sb, 256);
    string t = sb.ToString() ?? "";
    // v1463 - EXACT title, and it must belong to the process we care about when a pid is
    // given. The old prefix rule also matched "TV DIABLO - Board" (the popout board runs in
    // its OWN process), so a visible board window satisfied "the console is up" while the
    // real console stayed hidden - the launcher then logged 'launch complete (window up)'
    // over exactly the dead-icon state this whole fix exists to detect.
    if (t == "TV DIABLO") {
      if (wantPid != 0) {
        uint wp; GetWindowThreadProcessId(h, out wp);
        if (wp != wantPid) return true;
      }
      if (IsWindowVisible(h)) { vis = h; return false; }   // visible is the best case - stop
      if (hid == IntPtr.Zero) hid = h;                     // remember first hidden, keep looking
    }
    return true;
  }
  // Returns TRUE only when the window is ACTUALLY visible afterwards. A cross-process
  // ShowWindow does not reliably un-hide a WinForms window that was born SW_HIDE (measured
  // on this machine), so we must verify rather than assume - otherwise the launcher logs
  // 'focused' for a window the human still cannot see. That lie is what hid this bug.
  //
  // unhide=false during a fresh boot: WinForms creates the form hidden and shows it itself a
  // moment later, so forcing SW_SHOW in that gap would paint a black frame before WebView2's
  // first paint - the very "black screen window" the user reported. Only force it as a
  // deliberate recovery (warm re-click, or after the boot grace period has expired).
  public static bool Focus(bool unhide) { return Focus(unhide, 0); }
  public static bool Focus(bool unhide, uint pid) {
    wantPid = pid;
    vis = IntPtr.Zero; hid = IntPtr.Zero; WasHidden = false; Raised = false; NowVisible = false;
    EnumWindows(Cb, IntPtr.Zero);
    IntPtr found = (vis != IntPtr.Zero) ? vis : hid;
    if (found == IntPtr.Zero) return false;
    WasHidden = (vis == IntPtr.Zero);
    if (WasHidden) {
      if (!unhide) return false;   // let the app show its own window; not a success yet
      ShowWindow(found, SW_SHOW);
    }
    if (IsIconic(found)) ShowWindow(found, SW_RESTORE);
    Raised = SetForegroundWindow(found);
    NowVisible = IsWindowVisible(found);
    return NowVisible;
  }
}
"@
    }
    if ([TvdFocusFast]::Focus($unhide, $wantPid)) {
      $how = 'visible'
      if ([TvdFocusFast]::WasHidden) { $how = 'un-hid' }
      Write-TvdLaunchLog ("focused existing TV DIABLO window [{0} raised={1}]" -f $how, [TvdFocusFast]::Raised)
      return $true
    }
    if ([TvdFocusFast]::WasHidden -and $unhide) {
      # Found it, but SW_SHOW did not stick - the window is unrecoverable from out here.
      Write-TvdLaunchLog 'found a HIDDEN TV DIABLO window but SW_SHOW did not stick - stale process; STOP+reopen'
    }
  } catch {
    Write-TvdLaunchLog ("focus note: {0}" -f $_)
  }
  return $false
}

function Show-TvdError([string]$text) {
  if ($Background) { Write-TvdLaunchLog ("sign-in start, no dialog: {0}" -f $text); return }
  try {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($text, 'TV DIABLO', 'OK', 'Error') | Out-Null
  } catch {
    Write-Host $text
  }
}

# ---------------------------------------------------------------------------
# v1417/v1448 SINGLE INSTANCE FIRST - before git/pip/python probes.
# ---------------------------------------------------------------------------
$mutex = $null
try {
  $created = $false
  $mutex = New-Object System.Threading.Mutex($true, 'Local\TV_DIABLO_WIN_LAUNCHER_v2', [ref]$created)
  if (-not $created) {
    Write-TvdLaunchLog 'launcher mutex busy - focus existing / exit quiet'
    # v1463 - another launcher is mid-spawn, so the window may still be pre-first-paint.
    # Do NOT force SW_SHOW here: that paints a black frame (the reported symptom).
    if (-not $Background) { [void](Focus-TvdWindow $false) }
    try { $mutex.Dispose() } catch {}
    $mutex = $null
    return
  }
} catch {
  Write-TvdLaunchLog ("mutex note: {0}" -f $_)
  $mutex = $null
}

# PATH seed - the already-up decision needs python so it can ask launcher_decide.py,
# the same rule the Mac launcher runs. Seeding here does not pull and does not spawn.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')
foreach ($p in @(
  "$env:LocalAppData\Programs\Python\Python312",
  "$env:LocalAppData\Programs\Python\Python312\Scripts",
  "$env:LocalAppData\Programs\Python\Python313",
  "$env:LocalAppData\Programs\Python\Python313\Scripts",
  "$env:LocalAppData\Microsoft\WinGet\Links",
  "$env:ProgramFiles\Git\cmd",
  "$env:USERPROFILE\.local\bin"
)) {
  if ((Test-Path -LiteralPath $p) -and ($env:Path -notlike "*$p*")) {
    $env:Path = "$p;$env:Path"
  }
}

function Real-Python {
  foreach ($c in @('pythonw', 'python', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    $src = [string]$cmd.Source
    if ($src -match 'WindowsApps\\(?:python|python3|pythonw)\.exe$') { continue }
    if ($c -eq 'py') {
      try {
        $v = & $c -3 -c "import sys; print(sys.version)" 2>$null
        if (-not $v) { continue }
        return @{ Cmd = 'py'; Prefix = @('-3') }
      } catch { continue }
    }
    if ($c -eq 'pythonw') {
      $py = Get-Command python -ErrorAction SilentlyContinue
      if ($py -and ([string]$py.Source) -notmatch 'WindowsApps\\') {
        return @{ Cmd = 'pythonw'; Prefix = @() }
      }
      continue
    }
    try {
      $v = & $c -c "import sys; print(sys.version)" 2>$null
      if (-not $v) { continue }
      return @{ Cmd = $c; Prefix = @() }
    } catch { continue }
  }
  return $null
}

function Stop-TvdListenerOnControlPort {
  # The process listening on 17772, so a consented update can bind. Never this launcher.
  $ids = @()
  try {
    $rows = netstat -ano -p tcp
  } catch {
    Write-TvdLaunchLog ("could not list :17772 ({0})" -f $_)
    return
  }
  foreach ($row in $rows) {
    $t = ([string]$row) -replace '\s+', ' '
    if ($t -notmatch ':17772 ') { continue }
    if ($t -notmatch 'LISTENING') { continue }
    $parts = $t.Trim().Split(' ')
    $procId = $parts[-1]
    if ($procId -match '^\d+$' -and [int]$procId -ne $PID) { $ids += [int]$procId }
  }
  $ids = @($ids | Select-Object -Unique)
  foreach ($procId in $ids) {
    try {
      Stop-Process -Id $procId -Force -ErrorAction Stop
      Write-TvdLaunchLog ("stopped the console serving :17772 pid={0}" -f $procId)
    } catch {
      Write-TvdLaunchLog ("could not stop pid {0}: {1}" -f $procId, $_)
    }
  }
  if ($ids.Count -gt 0) { Start-Sleep -Milliseconds 400 }
}

# ALREADY UP. One rule with the Mac launcher (launcher_decide.py):
# it came forward (exit 0) -> stop; the decision could not tell (any exit but 0 and 3) -> focus it and stop;
# it SAYS it is older than the disk or has no window (exit 3) -> his click is the consent
# to update, so this launch falls through, pulls, stops the old process, and boots the disk.
# A sign-in start (-Background) does neither: it leaves a running console exactly as it is.
$script:TvdReplaceRunning = $false
if (Test-TvdControlUp) {
  if ($Background) {
    Write-TvdLaunchLog 'sign-in start: control already up - left exactly as it is'
    if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
    return
  }
  $decidePy = Real-Python
  if (-not $decidePy) {
    # REG-1826 - no python means no decision and no update: this open can only bring forward what is running. It fell
    # through to the boot, which found no python either and showed 'No real Python found' over a console that was up.
    Write-TvdLaunchLog 'control is up but python was not found, so whether it matches the disk is UNKNOWN - this open cannot update it and brings the running console forward'
    # v1460 - a hidden window does not reliably come back from a focus from outside, so the console is asked to show
    # itself first - the same front request the shared decision makes for a console that is current.
    $frontArgs = @{ Uri = 'http://127.0.0.1:17772/api/window'; Method = 'Post'; UseBasicParsing = $true; TimeoutSec = 4;
                    ContentType = 'application/json'; Body = '{"do": "front", "from": "win-launcher-no-python"}' }
    try {
      $front = Invoke-WebRequest @frontArgs
      Write-TvdLaunchLog ("asked the running console forward: {0}" -f ([string]$front.Content).Trim())
    } catch {
      Write-TvdLaunchLog ("the running console could not be asked forward ({0}) - focusing it from outside" -f $_)
    }
    [void](Focus-TvdWindow)
    if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
    return
  } else {
    $decideCmd = $decidePy.Cmd
    $decidePrefix = @()
    if ($decidePy.Prefix) { $decidePrefix = @($decidePy.Prefix) }
    if ($decideCmd -eq 'pythonw') { $decideCmd = 'python' }
    $decideScript = Join-Path $here 'launcher_decide.py'
    try {
      $decideOut = & $decideCmd @decidePrefix $decideScript --port 17772 --from win-launcher 2>&1
      $decideRc = $LASTEXITCODE
    } catch {
      $decideOut = "$_"
      $decideRc = 1
    }
    if ($decideRc -eq 0) {
      Write-TvdLaunchLog ("running console brought forward: {0}" -f ([string]$decideOut).Trim())
      [void](Focus-TvdWindow)
      if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
      return
    }
    # REG-1940 - COULD NOT TELL IS NOT CONSENT. Only exit 3 is the console's own answer that it is older than the
    # disk or has no window. Exit 2 (a timeout under the game, an ok:false reply, a window mode the decision does
    # not know), exit 1 (python itself raised) and the catch above all used to fall through to
    # Stop-TvdListenerOnControlPort, which is Stop-Process -Force on a console that may be filming his session.
    if ($decideRc -ne 3) {
      Write-TvdLaunchLog ("could not tell whether the running console is current (decide exit {0}: {1}) - it is left running and focused, never stopped on a guess" -f $decideRc, ([string]$decideOut).Trim())
      [void](Focus-TvdWindow)
      if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
      return
    }
    Write-TvdLaunchLog ("running console is older than the disk or has no window (decide exit {0}: {1}) - this open updates it" -f $decideRc, ([string]$decideOut).Trim())
    $script:TvdReplaceRunning = $true
  }
}

$py = Real-Python
if (-not $py) {
  Write-TvdLaunchLog 'No real Python found'
  if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
  Show-TvdError "No real Python found. Re-run the installer.`n`nLog: $launchLog"
  return
}

# v1447 - webview probe once; cache result so warm launches skip pip
$wvCache = Join-Path $here '.webview_ok'
$needWv = -not (Test-Path -LiteralPath $wvCache)
if ($needWv) {
  $probe = if ($py.Cmd -eq 'py') { @('py', '-3', '-c', 'import webview') }
           elseif ($py.Cmd -eq 'pythonw') { @('python', '-c', 'import webview') }
           else { @($py.Cmd, '-c', 'import webview') }
  $ok = $false
  try {
    & $probe[0] $probe[1..($probe.Length - 1)] 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok = $true }
  } catch {}
  if (-not $ok) {
    Write-TvdLaunchLog 'installing pywebview (first run)'
    $pip = if ($py.Cmd -eq 'py') { @('py', '-3', '-m', 'pip', 'install', '--user', '--quiet', 'pywebview>=5.0') }
           elseif ($py.Cmd -eq 'pythonw') { @('python', '-m', 'pip', 'install', '--user', '--quiet', 'pywebview>=5.0') }
           else { @($py.Cmd, '-m', 'pip', 'install', '--user', '--quiet', 'pywebview>=5.0') }
    try { & $pip[0] $pip[1..($pip.Length - 1)] 2>$null | Out-Null } catch {}
  } else {
    try { Set-Content -LiteralPath $wvCache -Value '1' -Encoding ASCII } catch {}
  }
}

# #227 - Pillow decodes every frame this console films (tv_diablo, chronicle_calibrate). MEASURED on
# the ALT 2026-09-24: Python 3.12.10 had pywebview and NO Pillow, so every frame it captured was
# unreadable and nothing said so. Same probe-once-and-cache shape as pywebview above; the doctor row
# 'this machine can decode a frame' says whether it worked.
$pilCache = Join-Path $here '.pillow_ok'
if (-not (Test-Path -LiteralPath $pilCache)) {
  $probe = if ($py.Cmd -eq 'py') { @('py', '-3', '-c', 'import PIL') }
           elseif ($py.Cmd -eq 'pythonw') { @('python', '-c', 'import PIL') }
           else { @($py.Cmd, '-c', 'import PIL') }
  $ok = $false
  try {
    & $probe[0] $probe[1..($probe.Length - 1)] 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok = $true }
  } catch {}
  if (-not $ok) {
    Write-TvdLaunchLog 'installing Pillow (frames cannot be decoded without it)'
    $pip = if ($py.Cmd -eq 'py') { @('py', '-3', '-m', 'pip', 'install', '--user', '--quiet', 'Pillow') }
           elseif ($py.Cmd -eq 'pythonw') { @('python', '-m', 'pip', 'install', '--user', '--quiet', 'Pillow') }
           else { @($py.Cmd, '-m', 'pip', 'install', '--user', '--quiet', 'Pillow') }
    try { & $pip[0] $pip[1..($pip.Length - 1)] 2>$null | Out-Null } catch {}
  } else {
    try { Set-Content -LiteralPath $pilCache -Value '1' -Encoding ASCII } catch {}
  }
}

# v1447 - NEVER open a blocking claude login shell on Desktop double-click (extra window lag).
# Doctor/ON AIR will surface Claude missing if needed.

# v1445 - time-boxed auto-pull AFTER we know we must spawn (not on warm re-open).
# Cap wall time so a hung git never freezes the Desktop icon for 30s+.
if (-not $env:TV_NO_AUTO_PULL) {
  $trackedDirty = $false
  try {
    $porc = @(git -C $repo status --porcelain 2>$null)
    foreach ($line in $porc) {
      if ($line -and ($line -notmatch '^\?\?')) { $trackedDirty = $true; break }
    }
  } catch {}
  # A file that matches the fetched origin, CR ignored, is the update, not an edit.
  # The same rule as the running console. This script runs before that process.
  $pullRc = 1
  $pullWhy = 'could not tell whether the changed files are the update'
  try {
    $pullCmd = $py.Cmd
    $pullPrefix = @()
    if ($py.Prefix) { $pullPrefix = @($py.Prefix) }
    if ($pullCmd -eq 'pythonw') { $pullCmd = 'python' }
    $pullScript = Join-Path $here 'launcher_pull.py'
    $pullWhy = & $pullCmd @pullPrefix $pullScript --repo $repo --apply 2>&1
    $pullRc = $LASTEXITCODE
    $pullWhy = ($pullWhy | Out-String).Trim()
  } catch {
    $pullRc = 1
  }
  $pullProceed = $false
  if ($pullRc -eq 0) {
    $pullProceed = $true
    if ($pullWhy -and ($pullWhy -ne 'clean')) {
      Write-TvdLaunchLog ("auto-pull: {0}" -f $pullWhy)
    }
  } elseif ($pullRc -eq 2) {
    Write-TvdLaunchLog ("skip auto-pull: {0}" -f $pullWhy)
  } elseif ($trackedDirty) {
    Write-TvdLaunchLog 'skip auto-pull: tracked files modified'
  } else {
    $pullProceed = $true
  }
  if ($pullProceed) {
    try {
      $env:GIT_TERMINAL_PROMPT = '0'
      # shallow-ish: fetch with 10s kill via job
      # REG-1667 (the v3541 cross-family eye) - FAST-FORWARD ONLY, NEVER RESET. A refused fast-forward on a clean
      # tree means commits here that origin does not have, and the old 'reset --hard origin/main' threw them away -
      # since REG-1660 at every sign-in, with no dialog. The console's own update lane (_pull_once) has always
      # refused instead and says why on the doctor row 'this checkout can update': one rule for both doors.
      $fetchJob = Start-Job -ScriptBlock {
        param($r)
        git -C $r fetch origin --quiet 2>$null
        git -C $r merge --ff-only origin/main 2>$null
        "ffexit=$LASTEXITCODE"
      } -ArgumentList $repo
      $null = Wait-Job $fetchJob -Timeout 12
      if ($fetchJob.State -eq 'Running') {
        # v1460 - Stop-Job has NO -Force parameter on Windows PowerShell 5.1. The old call
        # threw a ParameterBindingException straight past -ErrorAction into the outer catch,
        # so the job was NEVER stopped: it kept running and its merge --ff-only / reset --hard
        # rewrote control_app.py + control_ui.html ~0.6s AFTER python had already started.
        # The app then served swapped UI files from stale code and the window never came up.
        # Stop it for real, and WAIT for it to die before any spawn so the working tree is
        # never rewritten under a booting app. (ASCII only here - see REG-046.)
        Stop-Job -Job $fetchJob -ErrorAction SilentlyContinue
        $null = Wait-Job $fetchJob -Timeout 5
        # v1463 - only THIS case can leave an orphaned git.exe still rewriting the tree, so
        # it is the only case that pays for Wait-TvdGitQuiet before the spawn.
        $script:TvdPullJobStopped = $true
        Write-TvdLaunchLog ("auto-pull: timed out (12s) - stopped job state={0}; launching with local tree" -f $fetchJob.State)
      } else {
        $ffOut = @(Receive-Job $fetchJob -ErrorAction SilentlyContinue | ForEach-Object { "$_" })
        $ffLine = @($ffOut | Where-Object { $_ -like 'ffexit=*' } | Select-Object -Last 1)
        if ($ffLine.Count -and $ffLine[0] -ne 'ffexit=0') {
          Write-TvdLaunchLog ("auto-pull: the fast-forward was refused ({0}) - launching with the local tree, nothing reset; the console's update lane says why" -f $ffLine[0])
        } else {
          Write-TvdLaunchLog 'auto-pull: done'
        }
      }
      Remove-Job $fetchJob -Force -ErrorAction SilentlyContinue
    } catch {
      Write-TvdLaunchLog ("auto-pull error: {0}" -f $_)
    }
  }
} else {
  Write-TvdLaunchLog 'skip auto-pull: TV_NO_AUTO_PULL set'
}

# v1460 - the working tree must be QUIET before we spawn python. Stop-Job kills the job's
# runspace but a git.exe it already launched can outlive it and finish its merge/reset a
# moment later - which is exactly how control_app.py + control_ui.html got rewritten 0.6s
# after python started. Bounded wait; never blocks the icon for long.
function Wait-TvdGitQuiet([int]$maxMs = 6000) {
  $waited = 0
  while ($waited -lt $maxMs) {
    $g = @(Get-Process git -ErrorAction SilentlyContinue)
    if ($g.Count -eq 0) {
      if ($waited -gt 0) { Write-TvdLaunchLog ("git quiet after {0}ms" -f $waited) }
      return $true
    }
    Start-Sleep -Milliseconds 250
    $waited += 250
  }
  Write-TvdLaunchLog ("git still running after {0}ms - spawning anyway (tree may shift)" -f $maxMs)
  return $false
}

# Re-check after pull: another click may have won
if (Test-TvdControlUp) {
  if ($Background) {
    # REG-1667 (the v3541 cross-family eye) - a sign-in start leaves a console that came up DURING the pull exactly
    # as it is, the same as one that was already up: only the first check honoured -Background, so a console slow
    # to answer at sign-in was unhidden and brought over his desktop by the shortcut that promised not to.
    Write-TvdLaunchLog 'sign-in start: control came up during pull - left exactly as it is'
    if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
    return
  }
  if ($script:TvdReplaceRunning) {
    Write-TvdLaunchLog 'the older console is still serving after the pull - stopping it so this open boots the disk'
    Stop-TvdListenerOnControlPort
  } else {
    Write-TvdLaunchLog 'control came up during pull - focus only'
    [void](Focus-TvdWindow)
    if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
    return
  }
}

$control = Join-Path $here 'control_app.py'
$ui = Join-Path $here 'control_ui.html'
$capture = Join-Path $here 'capture_win.ps1'
$shipPath = Join-Path $here 'WINDOWS_SHIP.json'
if (-not (Test-Path -LiteralPath $control) -or -not (Test-Path -LiteralPath $ui)) {
  Write-TvdLaunchLog 'control_app.py or control_ui.html missing'
  if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
  Show-TvdError "Control app files missing. Re-run WINDOWS installer.`nLog: $launchLog"
  return
}
if (-not (Test-Path -LiteralPath $capture)) {
  Write-TvdLaunchLog 'capture_win.ps1 missing'
  if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
  Show-TvdError "Windows capture missing (capture_win.ps1).`nLog: $launchLog"
  return
}

$shipVer = '?'
if (Test-Path -LiteralPath $shipPath) {
  try {
    $ship = Get-Content -LiteralPath $shipPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($ship.platform -ne 'windows') {
      if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
      Show-TvdError "WINDOWS_SHIP.platform=$($ship.platform) - this launcher is Windows only."
      return
    }
    $shipVer = [string]$ship.ver
    Write-TvdLaunchLog ("Windows ship ver={0}" -f $shipVer)
  } catch {
    Write-TvdLaunchLog ("WINDOWS_SHIP.json read failed: {0}" -f $_)
  }
}

$exeCmd = Get-Command $py.Cmd -ErrorAction SilentlyContinue
$exePath = if ($exeCmd) { [string]$exeCmd.Source } else { $py.Cmd }
if ($py.Cmd -eq 'py') {
  $argLine = '-3 "' + $control + '" --open'
} else {
  $argLine = '"' + $control + '" --open'
}
if ($Background) { $argLine += ' --background' }   # REG-1660 - hidden from its first second
# v3860 - THE CONSOLE ITSELF RUNS IN UTF-8 MODE. control_app.py sets PYTHONUTF8 in os.environ at import (v1463), and
# that reaches every CHILD - but a running interpreter cannot change its own mode, so the console process stayed in
# the ANSI codepage (cp1255 here, cp1252 on Dean's PC): its own subprocess text reads decoded node's UTF-8 in cp1255
# (the reader thread dies -> stdout None, or a middle dot comes back as two letters), and its own open() calls without encoding= did too.
# MEASURED 2026-11-04 on the new Konyo ALT PC: 94 law cases FAILED(3F/20E) in the ANSI codepage, OK(99) with only
# PYTHONUTF8=1 added. The mode is chosen at interpreter START, so it is set here, where the console is started.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# v1460/v1463 - never spawn while OUR timed-out pull job may still be rewriting the tree.
# v1463: only wait when that actually happened. Wait-TvdGitQuiet matches git.exe machine-wide
# (it cannot tell whose git it is), so calling it unconditionally made every cold launch hostage
# to any unrelated git in another terminal or an editor - re-adding the very icon latency v1445
# removed - and it ran even under TV_NO_AUTO_PULL where this launcher never touched git at all.
if ($script:TvdPullJobStopped) { [void](Wait-TvdGitQuiet) }
if ($script:TvdReplaceRunning) { Stop-TvdListenerOnControlPort }
$controlStamp = $null
try { $controlStamp = (Get-Item -LiteralPath $control).LastWriteTime } catch {}

function Write-TvdStaleCodeWarning {
  # v1463 - hoisted out of the `if ($ready)` block. It used to live INSIDE the success path,
  # so it could never fire in the failure mode it was written to diagnose (python dying or
  # never serving because the tree moved under it). Now every terminal path calls it.
  if (-not $controlStamp) { return }
  try {
    $now = (Get-Item -LiteralPath $control).LastWriteTime
    if ($now -ne $controlStamp) {
      Write-TvdLaunchLog ("WARN control_app.py was rewritten during boot ({0} -> {1}) - app is running stale code; relaunch" -f $controlStamp, $now)
    }
  } catch {}
}

Write-TvdLaunchLog ("launch FileName={0} Args={1} WD={2}" -f $exePath, $argLine, $repo)

try {
  # pythonw = no console flash (pythonw.exe is a GUI-subsystem binary - it has NO console).
  #
  # v1460 ROOT CAUSE of the dead Desktop icon: v1444 added -WindowStyle Hidden here. That
  # sets STARTUPINFO.wShowWindow = SW_HIDE on the child, and .NET WinForms applies the
  # startup show-command to the process's FIRST top-level window - which is pywebview's
  # WebView2 host window. So the app window was created correctly (right title, 1120x737,
  # on-screen) and then never shown: control answered :17772, /api/status said ready, the
  # launcher logged 'launch complete', and the user saw nothing but two PowerShell consoles
  # blink. Proven A/B on this machine: same script spawned Hidden -> IsWindowVisible False,
  # spawned default -> True. The flag was never needed (pythonw has no console to hide).
  $proc = Start-Process -FilePath $exePath -ArgumentList $argLine -WorkingDirectory $repo -PassThru
  $sinceSpawn = [System.Diagnostics.Stopwatch]::StartNew()   # v1463 - window budget starts HERE
  Write-TvdLaunchLog ("started pid={0}" -f $proc.Id)
} catch {
  Write-TvdLaunchLog ("Start-Process FAILED: {0}" -f $_)
  if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose() }
  Show-TvdError "TV DIABLO failed to start Python.`n`n$_`n`nLog: $launchLog"
  return
}

# v1448 - ready wait uses FAST status probe (max ~8s), not 45s doctor ok:true
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 400
  if (Test-TvdControlUp) {
    $ready = $true
    Write-TvdLaunchLog ("ready status OK i={0} pid={1}" -f $i, $proc.Id)
    break
  }
  if ($proc.HasExited -and $i -gt 3) {
    Start-Sleep -Milliseconds 400
    if (Test-TvdControlUp) { $ready = $true; break }
    Write-TvdLaunchLog ("python exited early code={0}" -f $proc.ExitCode)
    break
  }
}

# Release launcher mutex ASAP so a second click only FOCUSES (does not queue another full launch)
if ($mutex) { try { $mutex.ReleaseMutex() | Out-Null } catch {}; $mutex.Dispose(); $mutex = $null }

if ($ready -and $Background) {
  Write-TvdLaunchLog ("sign-in start complete: control up, window hidden by design (pid {0})" -f $proc.Id)
  return
}

if ($ready) {
  # v1460 Law 9 - a /api/status answer is NOT proof of a window. v1448 traded the slow
  # doctor probe for this fast one and started logging 'launch complete' for a process that
  # served :17772 with no window at all, which is how the dead-icon state stayed invisible
  # in the log for days. Give WebView2 a bounded chance to paint, then log what is TRUE.
  #
  # v1463 - measure from SPAWN, not from the status answer. Control can answer ~1s in while
  # WebView2's first paint takes far longer on a cold start, so the old 12x400ms clock (which
  # only began once status replied) both forced SW_SHOW inside the real paint window and then
  # told the user to STOP+reopen a launch that was about to succeed. Budget is now generous,
  # the un-hide only fires well past any normal paint, and the window must belong to OUR pid.
  $win = $false
  $unhideAfterMs = 8000
  $giveUpMs = 20000
  while ($sinceSpawn.ElapsedMilliseconds -lt $giveUpMs) {
    if (Focus-TvdWindow ($sinceSpawn.ElapsedMilliseconds -ge $unhideAfterMs) $proc.Id) { $win = $true; break }
    if ($proc.HasExited) { break }
    Start-Sleep -Milliseconds 400
  }
  Write-TvdStaleCodeWarning
  if ($win) {
    Write-TvdLaunchLog ("launch complete (window up after {0}ms)" -f $sinceSpawn.ElapsedMilliseconds)
  } else {
    Write-TvdLaunchLog ("WARN control up but NO TV DIABLO window from pid {0} after {1}ms - headless/hidden; STOP+reopen if the icon stays dead" -f $proc.Id, $sinceSpawn.ElapsedMilliseconds)
  }
  return
}

# Soft: process still alive - window may paint under WebView2 cold start; no scary dialog
if (-not $proc.HasExited) {
  Write-TvdLaunchLog 'status slow but process alive - exit quiet (window coming)'
  # v1463 - still booting; never force SW_SHOW over an unpainted WebView2 surface.
  if (-not $Background) { [void](Focus-TvdWindow $false $proc.Id) }
  Write-TvdStaleCodeWarning
  return
}
Write-TvdStaleCodeWarning

Write-TvdLaunchLog 'launch FAIL: process dead and status down'
Show-TvdError (
  "TV DIABLO did not come up.`n`nPython exited and control is down.`n" +
  "Log: $launchLog`n`nTry: powershell -File `"$PSCommandPath`""
)
