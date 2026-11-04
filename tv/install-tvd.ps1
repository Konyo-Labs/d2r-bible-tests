#  TV DIABLO - one-shot Windows installer (Windows only  -  v1404)
#
#     irm https://bull-4-u.com/d2r/install-tvd.ps1 | iex
#
# One paste: Git + Python + pywebview + Claude Code + Grok CLI (optional SuperGrok
# vision lane), clones the bible repo, drops Desktop "TV DIABLO" -> real native app
# window (pywebview / Edge WebView2, NOT Chrome). Windows control UI (pywebview / WebView2):
# ON/OFF/STOP/RESTART/SIM  -  hidden agent. Grok stays OFF until you authorize once.
#
# Served as text/plain so `irm | iex` always gets a string.
$ErrorActionPreference = 'Stop'

# v1404 WINDOWS ONLY - never run Mac scripts on this PC; never claim Mac parity here.
if ($env:OS -ne 'Windows_NT') {
  Write-Host 'TV DIABLO installer: Windows only. Use the Mac installer on macOS.' -ForegroundColor Red
  return
}
$env:TV_PLATFORM = 'windows'
$env:TV_OS = 'windows'

$repoUrl  = 'https://github.com/KonyoDigital/d2r-bible-tests.git'
$repoDir  = Join-Path $HOME 'd2r_bible_tests'

function Say($m)  { Write-Host "TV DIABLO  $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "   OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "   !!  $m" -ForegroundColor Yellow }

try {
  [Net.ServicePointManager]::SecurityProtocol = `
    [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch {}

function Refresh-Path {
  $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $user    = [Environment]::GetEnvironmentVariable('Path', 'User')
  $env:Path = @($machine, $user) -join ';'
  $extras = @(
    (Join-Path $env:ProgramFiles 'Git\cmd'),
    (Join-Path $env:ProgramFiles 'Git\bin'),
    (Join-Path ${env:ProgramFiles(x86)} 'Git\cmd'),
    (Join-Path $env:LocalAppData 'Programs\Python\Python312'),
    (Join-Path $env:LocalAppData 'Programs\Python\Python312\Scripts'),
    (Join-Path $env:LocalAppData 'Programs\Python\Python313'),
    (Join-Path $env:LocalAppData 'Programs\Python\Python313\Scripts'),
    (Join-Path $env:LocalAppData 'Programs\Python\Python311'),
    (Join-Path $env:LocalAppData 'Programs\Python\Python311\Scripts'),
    (Join-Path $env:LocalAppData 'Microsoft\WinGet\Links'),
    (Join-Path $env:USERPROFILE '.local\bin'),
    (Join-Path $env:USERPROFILE 'AppData\Local\Microsoft\WinGet\Packages')
  )
  foreach ($p in $extras) {
    if ($p -and (Test-Path -LiteralPath $p) -and ($env:Path -notlike ("*{0}*" -f $p))) {
      $env:Path = "$p;$env:Path"
    }
  }
}

function Have($cmd) {
  return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Real-Python {
  foreach ($c in @('python', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    $src = [string]$cmd.Source
    if ($src -match 'WindowsApps\\(?:python|python3)\.exe$') { continue }
    if ($c -eq 'py') {
      try {
        $v = & $c -3 -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -ne 0 -and -not $v) { continue }
      } catch { continue }
    } else {
      try {
        $v = & $c -c "import sys; print(sys.version)" 2>$null
        if (-not $v) { continue }
      } catch { continue }
    }
    return $c
  }
  return $null
}

function Winget-Install($id, $label) {
  Say "installing $label..."
  $wingetArgs = @('install', '-e', '--id', $id, '--silent',
                  '--accept-package-agreements', '--accept-source-agreements',
                  '--disable-interactivity')
  & winget @wingetArgs | Out-Null
  Refresh-Path
  Start-Sleep -Seconds 1
  Refresh-Path
}

Say "installer (Windows only  -  v1404) - one shot, then Desktop TV DIABLO = the control app"

if (-not (Have 'winget')) {
  Warn "winget not found - install 'App Installer' from the Microsoft Store, then re-run this line."
  return
}

Refresh-Path
if (-not (Have 'git')) {
  Winget-Install 'Git.Git' 'Git'
}
if (Have 'git') { Ok "git $((git --version) -replace 'git version ','')" } else {
  Warn "git still missing - close this window, open a NEW PowerShell, re-run the install line."
  return
}

$py = Real-Python
if (-not $py) {
  Winget-Install 'Python.Python.3.12' 'Python 3.12'
  $py = Real-Python
}
if ($py) { Ok "python ($py)" } else {
  Warn "python still missing (or only the Windows Store stub is installed)."
  Warn "turn OFF 'App execution aliases' for python.exe in Settings -> Apps -> Advanced, then re-run."
  return
}

# -- pywebview (real native window via Edge WebView2 - not Chrome) ------------
Say "installing pywebview (native app window)..."
try {
  & $py -m pip install --user --quiet 'pywebview>=5.0' | Out-Null
  # #227 - and Pillow: without it no frame this console films can be decoded (measured on the ALT)
  & $py -m pip install --user --quiet 'Pillow' | Out-Null
  # REG-1719 - and numpy: the inventory lattice measures a frame with it; the ALT never had it, so the vault's pixel
  # cross-check never ran on a Windows PC. (The console also installs it at boot, for PCs that only self-update.)
  & $py -m pip install --user --quiet 'numpy' | Out-Null
  # #50 (REG-1457) - and websocket-client: every PC now proves its own gates, and the browser laws drive
  # Chrome/Edge over DevTools with it. The ALT had never had it; the self-prove lane also installs it.
  & $py -m pip install --user --quiet 'websocket-client' | Out-Null
  # v770 - pywebview on Windows NEEDS the Edge WebView2 Runtime; locked-down PCs lack it and
  # the app silently falls to a browser. Bootstrap it loudly if missing.
  $wv2 = Test-Path "$env:ProgramFiles (x86)\Microsoft\EdgeWebView\Application" -PathType Container
  if (-not $wv2) { $wv2 = Test-Path "${env:ProgramFiles(x86)}\Microsoft\EdgeWebView\Application" }
  if (-not $wv2) {
    Say "installing Edge WebView2 Runtime (the native window engine)..."
    winget install -e --id Microsoft.EdgeWebView2Runtime --silent --accept-package-agreements --accept-source-agreements | Out-Null
  }
  Ok "pywebview (native window  -  WebView2)"
} catch {
  Warn "pywebview pip install failed - app will retry on first launch / browser fallback"
}

# -- bible repo FIRST (so Desktop shortcut always lands even if Claude install flakes) --
# REG-2183 - A COPY THE UPDATE RULE CALLS "LOCAL WORK" NEVER UPDATES AGAIN. Measured 2026-10-13: Dean's PC sat on v3577,
# 1,063 behind, and the ALT on v3668, 105 behind, both refused as "local tracked edits". On the ALT the edits were a
# DRAFT of v3668 written into the tree at 20:43 on 10-11 that shipped later in another form - nobody's work, and no
# shipped blob matches it, so no automatic rule can call it the update. This is the one door out, and it is HIS
# (or Dean's) Enter key: name the files, save every one of them plus a patch and the old HEAD, then put the copy on
# the update. Only tracked files move; gitignored stores (his ledgers, reels, the vault) are never touched, and an
# untracked file the update would land on is saved first. TVD_UPDATE_ANYWAY=1 answers the question without a prompt.
function Save-And-Update([string]$why) {
  # Windows PowerShell 5.1 turns a native command's stderr into a terminating error under 'Stop', and autocrlf=true
  # makes git print "LF will be replaced by CRLF" warnings there - so every git call here runs under 'Continue',
  # and the one thing that must fail closed (saving his copy) throws on purpose with -ErrorAction Stop.
  $oldEap2 = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    return (Save-And-Update-Inner $why)
  } finally {
    $ErrorActionPreference = $oldEap2
  }
}

function Save-And-Update-Inner([string]$why) {
  Warn $why
  $rows = @(& git --no-pager -C $repoDir status --porcelain --untracked-files=no 2>$null | Where-Object { $_ })
  if ($LASTEXITCODE -ne 0) {
    Warn "git could not say what differs - nothing was changed"
    return $false
  }
  if ($rows.Count -eq 0) {
    Warn "nothing local differs, so there is nothing to save - the update was not applied"
    return $false
  }
  Say "This copy has files that differ from the update:"
  foreach ($r in ($rows | Select-Object -First 12)) { Write-Host ("      " + $r) }
  if ($rows.Count -gt 12) { Write-Host ("      ... and {0} more" -f ($rows.Count - 12)) }
  $go = [string]$env:TVD_UPDATE_ANYWAY
  if ($go -ne '1' -and $go -ne '0') {
    $ans = [string](Read-Host "TV DIABLO  Save a copy of them and update anyway? [Y/n]")
    if (($ans.Trim() -eq '') -or ($ans.Trim() -match '^[Yy]')) { $go = '1' } else { $go = '0' }
  }
  if ($go -ne '1') {
    Warn "left exactly as it is - nothing was changed"
    return $false
  }
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $bk = Join-Path (Join-Path $HOME 'd2r_update_backups') $stamp
  $saved = 0
  $inWay = 0
  try {
    New-Item -ItemType Directory -Force -Path (Join-Path $bk 'files') -ErrorAction Stop | Out-Null
    $head = [string](& git --no-pager -C $repoDir rev-parse HEAD 2>$null)
    Set-Content -LiteralPath (Join-Path $bk 'HEAD.txt') -Value $head -Encoding ascii -ErrorAction Stop
    # --output, never `>`: Windows PowerShell 5.1 redirects as UTF-16 and would corrupt the patch
    & git --no-pager -C $repoDir diff --binary ("--output=" + (Join-Path $bk 'changes.patch')) 2>$null
    foreach ($r in $rows) {
      $rel = ([string]$r).Substring(3).Trim().Trim('"')
      if ($rel -match ' -> ') { $rel = ($rel -split ' -> ')[-1].Trim().Trim('"') }
      $src = Join-Path $repoDir $rel
      if (Test-Path -LiteralPath $src -PathType Leaf) {
        $dst = Join-Path (Join-Path $bk 'files') $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) -ErrorAction Stop | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop
        $saved++
      }
    }
    # an untracked file sitting where the update lands a tracked one would be overwritten by the reset - save it too
    $tracked = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($p in @(& git --no-pager -C $repoDir ls-tree -r --name-only HEAD 2>$null)) { [void]$tracked.Add([string]$p) }
    $incoming = @(& git --no-pager -C $repoDir ls-tree -r --name-only origin/main 2>$null)
    if ($incoming.Count -eq 0) { throw "the update's file list could not be read" }
    foreach ($p in $incoming) {
      $p = [string]$p
      if ($tracked.Contains($p)) { continue }
      $src = Join-Path $repoDir $p
      if (Test-Path -LiteralPath $src -PathType Leaf) {
        $dst = Join-Path (Join-Path $bk 'untracked') $p
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) -ErrorAction Stop | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop
        $inWay++
      }
    }
  } catch {
    # a copy that was not saved is a copy the reset would destroy - nothing moves
    Warn ("could not save a copy ({0}) - nothing was changed" -f $_.Exception.Message)
    return $false
  }
  $rstErr = Join-Path $env:TEMP ("tvd-reset-" + [guid]::NewGuid().ToString("n") + ".txt")
  & git --no-pager -C $repoDir reset --hard origin/main --quiet 2>$rstErr
  $rstRc = $LASTEXITCODE
  if ($rstRc -ne 0) {
    $why2 = ""
    if (Test-Path -LiteralPath $rstErr) { $why2 = [string](Get-Content -LiteralPath $rstErr -Raw -ErrorAction SilentlyContinue) }
    Remove-Item -LiteralPath $rstErr -Force -ErrorAction SilentlyContinue
    if (-not $why2) { $why2 = "git reset exited $rstRc" }
    Warn ("the update could not be put in place: {0} (your files are saved in {1})" -f (($why2 -replace '\s+', ' ').Trim()), $bk)
    return $false
  }
  Remove-Item -LiteralPath $rstErr -Force -ErrorAction SilentlyContinue
  Ok ("bible repo is on the update - the {0} file(s) that differed are saved in {1}" -f $saved, $bk)
  if ($inWay -gt 0) { Ok ("{0} untracked file(s) the update replaced are saved there too" -f $inWay) }
  return $true
}

$script:TvdUpdated = $false
if (Test-Path (Join-Path $repoDir '.git')) {
  Say "updating the bible repo..."
  # This script is fetched fresh. The tree on disk may be an older build, so
  # its own launcher_pull.py may not exist yet. Fetch, then run the incoming
  # rule from a temp file copied as bytes. The rule does not move a clean tree.
  # Only after it allows the update does a fast-forward merge move HEAD.
  # A refusal is printed and is not fast-forwarded over. A reset happens only
  # inside that rule (plain modifications that match origin/main, HEAD an
  # ancestor, nothing untracked or ignored in the way).
  $env:GIT_TERMINAL_PROMPT = '0'
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $fetchErr = Join-Path $env:TEMP ("tvd-fetch-" + [guid]::NewGuid().ToString("n") + ".txt")
  & git --no-pager -C $repoDir fetch origin --quiet 2>$fetchErr
  $fetchRc = $LASTEXITCODE
  $ErrorActionPreference = $oldEap
  if ($fetchRc -ne 0) {
    $why = ""
    if (Test-Path -LiteralPath $fetchErr) {
      $why = (Get-Content -LiteralPath $fetchErr -Raw -ErrorAction SilentlyContinue)
    }
    Remove-Item -LiteralPath $fetchErr -Force -ErrorAction SilentlyContinue
    if (-not $why) { $why = "git fetch exited $fetchRc" }
    $why = (($why -replace '\s+', ' ').Trim())
    if ($why.Length -gt 400) { $why = $why.Substring(0, 400) }
    Warn ("could not fetch the update: {0}" -f $why)
  } else {
    Remove-Item -LiteralPath $fetchErr -Force -ErrorAction SilentlyContinue
    # REG-2183 - the rule runs from a temp FOLDER holding the update's own launcher_pull.py AND self_prove.py. It
    # asks self_prove whether a changed file is the console's own record; run alone from %TEMP% that import failed,
    # so every changed tree answered "could not tell" (exit 1) and the installer could never move it - measured on
    # the ALT 2026-10-13. Python puts the script's own folder first on sys.path, so the update's copy is the one used.
    $tmpDir = Join-Path $env:TEMP ("tvd-launcher-pull-" + [guid]::NewGuid().ToString("n"))
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
    $tmp = Join-Path $tmpDir 'launcher_pull.py'
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo.FileName = "git"
    $p.StartInfo.Arguments = "--no-pager -C `"$repoDir`" show `"origin/main:tv/launcher_pull.py`""
    $p.StartInfo.UseShellExecute = $false
    $p.StartInfo.RedirectStandardOutput = $true
    $p.StartInfo.RedirectStandardError = $true
    $p.StartInfo.CreateNoWindow = $true
    $p.StartInfo.StandardErrorEncoding = $utf8
    [void]$p.Start()
    $raw = New-Object System.IO.MemoryStream
    $p.StandardOutput.BaseStream.CopyTo($raw)
    $showErrText = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    $showRc = $p.ExitCode
    if ($showRc -ne 0) {
      $why = (($showErrText -replace '\s+', ' ').Trim())
      if (-not $why) { $why = "git show exited $showRc" }
      if ($why.Length -gt 400) { $why = $why.Substring(0, 400) }
      Warn ("the incoming update rule could not be read: {0}" -f $why)
    } else {
      try {
        [System.IO.File]::WriteAllBytes($tmp, $raw.ToArray())
        $spOut = Join-Path $tmpDir 'self_prove.py'
        $q = New-Object System.Diagnostics.Process
        $q.StartInfo.FileName = "git"
        $q.StartInfo.Arguments = "--no-pager -C `"$repoDir`" show `"origin/main:tv/self_prove.py`""
        $q.StartInfo.UseShellExecute = $false
        $q.StartInfo.RedirectStandardOutput = $true
        $q.StartInfo.RedirectStandardError = $true
        $q.StartInfo.CreateNoWindow = $true
        [void]$q.Start()
        $spRaw = New-Object System.IO.MemoryStream
        $q.StandardOutput.BaseStream.CopyTo($spRaw)
        [void]$q.StandardError.ReadToEnd()
        $q.WaitForExit()
        if ($q.ExitCode -eq 0) { [System.IO.File]::WriteAllBytes($spOut, $spRaw.ToArray()) }
        $ErrorActionPreference = 'Continue'
        if ($py -eq 'py') {
          $applyOut = & py -3 $tmp --repo $repoDir --apply 2>&1
        } else {
          $applyOut = & $py $tmp --repo $repoDir --apply 2>&1
        }
        $applyRc = $LASTEXITCODE
        $ErrorActionPreference = $oldEap
        $applyWhy = (($applyOut | Out-String) -replace '\s+', ' ').Trim()
        if (-not $applyWhy) { $applyWhy = "" }
        if ($applyWhy.Length -gt 400) { $applyWhy = $applyWhy.Substring(0, 400) }
        if ($applyRc -eq 0) {
          if ($applyWhy -and ($applyWhy -ne 'clean')) { Ok $applyWhy }
          $ffErr = Join-Path $env:TEMP ("tvd-ff-" + [guid]::NewGuid().ToString("n") + ".txt")
          $ErrorActionPreference = 'Continue'
          & git --no-pager -C $repoDir merge --ff-only origin/main --quiet 2>$ffErr
          $ffRc = $LASTEXITCODE
          $ErrorActionPreference = $oldEap
          if ($ffRc -ne 0) {
            $why = ""
            if (Test-Path -LiteralPath $ffErr) {
              $why = (Get-Content -LiteralPath $ffErr -Raw -ErrorAction SilentlyContinue)
            }
            Remove-Item -LiteralPath $ffErr -Force -ErrorAction SilentlyContinue
            if (-not $why) { $why = "git merge --ff-only exited $ffRc" }
            $why = (($why -replace '\s+', ' ').Trim())
            if ($why.Length -gt 400) { $why = $why.Substring(0, 400) }
            Warn ("could not fast-forward onto the update: {0}" -f $why)
          } else {
            Remove-Item -LiteralPath $ffErr -Force -ErrorAction SilentlyContinue
            Ok "bible repo is on the update"
            $script:TvdUpdated = $true
          }
        } else {
          if (-not $applyWhy) { $applyWhy = "the update was refused and gave no reason (exit $applyRc)" }
          if ($applyRc -eq 2) {
            # exit 2 = the rule protected local work; exit 1 = it could not tell, which never resets anything
            $script:TvdUpdated = [bool](Save-And-Update $applyWhy)
          } else {
            Warn $applyWhy
          }
        }
      } catch {
        Warn ("the update could not be applied: {0}" -f $_.Exception.Message)
      } finally {
        Remove-Item -LiteralPath $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        $ErrorActionPreference = $oldEap
      }
    }
  }
} else {
  Say "cloning the bible repo..."
  # v3861 - FULL HISTORY, NOT --depth 1: a one-commit clone left HEAD~1 unknown and filed 5 proofs BLIND on every new PC.
  # blob:none keeps it small: commits and trees now, file bodies only when something reads them.
  git clone --filter=blob:none $repoUrl $repoDir | Out-Null
}

# v761+ twin requires the control app surface
$need = @(
  'tv\start_tvd_win.ps1',
  'tv\control_app.py',
  'tv\control_ui.html',
  'tv\capture_win.ps1',
  'tv\tv_diablo.py',
  'bible.html'
)
foreach ($rel in $need) {
  if (-not (Test-Path (Join-Path $repoDir $rel))) {
    Warn "clone incomplete - missing $rel at $repoDir"
    Warn "git pull main (need v761+). Re-run this install line after the repo updates."
    return
  }
}
Ok "repo at $repoDir (control app present)"

# -- Node.js (REG-2484, #167) - the console's node lanes and its node-only laws need it. ONE door, the same one the
#    console asks: tv\node_runtime.py resolves node; where it is missing it fetches the pinned portable zip, checks its
#    SHA-256 before anything is extracted, and places it in %LOCALAPPDATA%\Programs\nodejs - no admin, no PATH or
#    registry change of his. A failure is said and never stops the install.
Say "checking Node.js (the console's node lanes)..."
$oldEapNode = $ErrorActionPreference
try {
  if (Test-Path -LiteralPath (Join-Path $repoDir 'tv\node_runtime.py')) {
    $ErrorActionPreference = 'Continue'
    $nodeOut = & $py "$repoDir\tv\node_runtime.py" --ensure 2>&1
    $nodeRc = $LASTEXITCODE
    $ErrorActionPreference = $oldEapNode
    $nodeWhy = (($nodeOut | Out-String) -replace '\s+', ' ').Trim()
    if ($nodeWhy.Length -gt 300) { $nodeWhy = $nodeWhy.Substring(0, 300) }
    if ($nodeRc -eq 0) { Ok $nodeWhy } else { Warn ("Node.js is not ready ({0}) - the install goes on without it" -f $nodeWhy) }
  } else {
    Warn "tv\node_runtime.py is not in this copy yet - Node.js was not checked; the install goes on"
  }
} catch {
  $ErrorActionPreference = $oldEapNode
  Warn ("the Node.js step failed: {0} - the install goes on without it" -f $_.Exception.Message)
}

# v1404 - pin Windows ship identity (no Mac mesh)
$shipPath = Join-Path $repoDir 'tv\WINDOWS_SHIP.json'
if (-not (Test-Path -LiteralPath $shipPath)) {
  Warn "WINDOWS_SHIP.json missing after clone - repo may be incomplete. Re-run after git pull."
} else {
  try {
    $ship = Get-Content -LiteralPath $shipPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($ship.platform -ne 'windows') {
      Warn "WINDOWS_SHIP.platform is '$($ship.platform)' - expected windows. Do not use Mac installers on this PC."
    } else {
      Ok "Windows ship $($ship.ver)  -  platform=windows  -  $($ship.name)"
    }
    $stampObj = [ordered]@{
      platform   = 'windows'
      shipVer    = [string]$ship.ver
      installedAt = (Get-Date).ToString('o')
      computer   = $env:COMPUTERNAME
      user       = $env:USERNAME
      repo       = $repoDir
      launcher   = 'tv\start_tvd_win.ps1'
      capture    = 'tv\capture_win.ps1'
      installer  = 'tv\install-tvd.ps1'
    }
    $stampPath = Join-Path $repoDir 'tv\.windows_install.json'
    ($stampObj | ConvertTo-Json) | Set-Content -LiteralPath $stampPath -Encoding UTF8
    Ok "install stamp: $stampPath"
  } catch {
    Warn "could not read WINDOWS_SHIP.json: $($_.Exception.Message)"
  }
}


# -- Claude Code (needed for vision ON AIR) -----------------------------------
# v784.1 - Windows PowerShell 5.1 often returns .Content as Byte[] for install.ps1;
#          Invoke-Expression then dies with "Cannot convert System.Byte[] to String".
#          Decode to UTF-8 string; fall backs: irm|iex, winget. NEVER abort before Desktop.
function Install-ClaudeCode {
  if (Have 'claude') { return $true }
  Say "installing Claude Code (Anthropic's official installer)..."

  # Path A - robust download + decode (fixes Byte[] crash on PS 5.1)
  try {
    $resp = Invoke-WebRequest -Uri 'https://claude.ai/install.ps1' -UseBasicParsing
    $scriptText = $null
    if ($null -eq $resp.Content) {
      throw "empty install.ps1 body"
    } elseif ($resp.Content -is [byte[]]) {
      $scriptText = [System.Text.Encoding]::UTF8.GetString($resp.Content)
    } else {
      $scriptText = [string]$resp.Content
    }
    if (-not $scriptText -or $scriptText.Length -lt 20) {
      throw "install.ps1 body too short"
    }
    Invoke-Expression $scriptText
  } catch {
    Warn "official install.ps1 path failed ($($_.Exception.Message))"
    # Path B - irm | iex (PowerShell may coerce bytes differently)
    try {
      Invoke-Expression (Invoke-RestMethod -Uri 'https://claude.ai/install.ps1')
    } catch {
      Warn "irm/iex path failed ($($_.Exception.Message))"
      # Path C - winget (when published)
      try {
        if (Have 'winget') {
          Say "trying winget Anthropic.ClaudeCode..."
          winget install -e --id Anthropic.ClaudeCode --silent --accept-package-agreements --accept-source-agreements 2>$null | Out-Null
        }
      } catch {}
    }
  }

  Refresh-Path
  Start-Sleep -Seconds 2
  Refresh-Path
  # common install locations not yet on PATH in this shell
  foreach ($p in @(
    (Join-Path $env:USERPROFILE '.local\bin'),
    (Join-Path $env:LocalAppData 'Programs\claude'),
    (Join-Path $env:LocalAppData 'claude'),
    (Join-Path $env:APPDATA 'npm')
  )) {
    if ((Test-Path -LiteralPath $p) -and ($env:Path -notlike "*$p*")) {
      $env:Path = "$p;$env:Path"
    }
  }
  return (Have 'claude')
}

Refresh-Path
$claudeOk = Install-ClaudeCode
if ($claudeOk) {
  Ok "claude code"
} else {
  Warn "claude still missing - vision ON AIR needs it."
  Warn "install manually: https://docs.anthropic.com/en/docs/claude-code"
  Warn "or in a NEW PowerShell:  irm https://claude.ai/install.ps1 | iex"
  Warn "Desktop app will still be created - log into Claude before ON."
}

# -- Grok Build CLI (optional SuperGrok vision lane  -  G5  -  never required) ----
# Official xAI installer (same spirit as Claude Code). Cousin can leave Grok OFF.
# Authorize once later: console  Authorize Grok, or:  grok login
function Install-GrokCli {
  if (Have 'grok') { return $true }
  Say "installing Grok CLI (xAI SuperGrok  -  optional vision lane)..."
  try {
    $resp = Invoke-WebRequest -Uri 'https://x.ai/cli/install.ps1' -UseBasicParsing
    $scriptText = $null
    if ($null -eq $resp.Content) {
      throw "empty install.ps1 body"
    } elseif ($resp.Content -is [byte[]]) {
      $scriptText = [System.Text.Encoding]::UTF8.GetString($resp.Content)
    } else {
      $scriptText = [string]$resp.Content
    }
    if (-not $scriptText -or $scriptText.Length -lt 20) {
      throw "install.ps1 body too short"
    }
    Invoke-Expression $scriptText
  } catch {
    Warn "official Grok install.ps1 path failed ($($_.Exception.Message))"
    try {
      Invoke-Expression (Invoke-RestMethod -Uri 'https://x.ai/cli/install.ps1')
    } catch {
      Warn "Grok irm/iex path failed ($($_.Exception.Message))"
    }
  }
  Refresh-Path
  Start-Sleep -Seconds 2
  Refresh-Path
  foreach ($p in @(
    (Join-Path $env:USERPROFILE '.grok\bin'),
    (Join-Path $env:USERPROFILE '.local\bin'),
    (Join-Path $env:LocalAppData 'Programs\grok'),
    (Join-Path $env:LocalAppData 'grok')
  )) {
    if ((Test-Path -LiteralPath $p) -and ($env:Path -notlike "*$p*")) {
      $env:Path = "$p;$env:Path"
    }
  }
  return (Have 'grok')
}

Refresh-Path
$grokOk = Install-GrokCli
if ($grokOk) {
  Ok "grok cli (optional - authorize later in console or: grok login)"
} else {
  Warn "grok CLI not installed - optional. Grok Eyes stays OFF until you install SuperGrok CLI."
  Warn "manual:  irm https://x.ai/cli/install.ps1 | iex   then:  grok login"
}

# Desktop shortcut -> start_tvd_win.ps1 -> pythonw + pywebview native window
$ws  = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
# OneDrive Desktop redirect (common on Windows 11)
$deskCandidates = @(
  $desktop,
  (Join-Path $env:USERPROFILE 'Desktop'),
  (Join-Path $env:USERPROFILE 'OneDrive\Desktop'),
  (Join-Path $env:USERPROFILE 'OneDrive - Personal\Desktop')
) | Select-Object -Unique
$lnkPath = $null
foreach ($d in $deskCandidates) {
  if ($d -and (Test-Path -LiteralPath $d)) {
    $lnkPath = Join-Path $d 'TV DIABLO.lnk'
    break
  }
}
if (-not $lnkPath) {
  $lnkPath = Join-Path $desktop 'TV DIABLO.lnk'
}
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = 'powershell.exe'
# Hidden host shell only - the app window is pywebview (pythonw), not this console
$lnk.Arguments        = "-NoLogo -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$repoDir\tv\start_tvd_win.ps1`""
$lnk.WorkingDirectory = $repoDir
$ico = Join-Path $repoDir 'tv\appicon.ico'
if (Test-Path -LiteralPath $ico) {
  $lnk.IconLocation = $ico
} else {
  $lnk.IconLocation = 'powershell.exe,0'
}
$lnk.Description      = 'TV DIABLO Windows - native WebView2 control (NOT Mac  -  hidden scanner  -  Claude)'
$lnk.Save()
Ok "Desktop shortcut: $lnkPath"

# Also Start Menu for discoverability
try {
  $startDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
  if (Test-Path $startDir) {
    $sl = $ws.CreateShortcut((Join-Path $startDir 'TV DIABLO.lnk'))
    $sl.TargetPath       = $lnk.TargetPath
    $sl.Arguments        = $lnk.Arguments
    $sl.WorkingDirectory = $lnk.WorkingDirectory
    $sl.IconLocation     = $lnk.IconLocation
    $sl.Description      = $lnk.Description
    $sl.Save()
    Ok "Start Menu: TV DIABLO"
  }
} catch {}

# REG-2183 - after an update the app is opened for him: the launcher sees the running console is older than the
# disk and swaps it (launcher_decide REPLACE). Never from an SSH session - that would boot it on no desktop.
if ($script:TvdUpdated -and -not $env:SSH_CONNECTION -and -not $env:TVD_NO_START) {
  try {
    Start-Process -FilePath $lnkPath
    Ok "opening TV DIABLO on the update"
  } catch {
    Warn ("could not open TV DIABLO ({0}) - double-click it on the Desktop" -f $_.Exception.Message)
  }
}
Say "DONE. Double-click TV DIABLO on your Desktop (or Start Menu)."
Say "Native app window (not Chrome)  -  ON / OFF / STOP / RESTART / SIM  -  one window."
if (-not $claudeOk) {
  Warn "finish Claude Code install, then re-open TV DIABLO and press ON AIR."
}
$credFile = Join-Path $HOME '.claude\.credentials.json'
if (-not (Test-Path $credFile)) {
  Warn "first run may walk you through logging into your own Claude account (once)."
}
if ($grokOk) {
  $gAuth = Join-Path $HOME '.grok\auth.json'
  if (-not (Test-Path $gAuth)) {
    Warn "Grok CLI ready - open TV DIABLO ->  advanced ->  Authorize Grok (browser once), or: grok login"
  } else {
    Ok "Grok already authorized on this PC (no re-login needed)"
  }
}
echo ""
echo "   Windows only:  irm https://bull-4-u.com/d2r/install-tvd.ps1 | iex"
echo "   Ship:         tv\WINDOWS_SHIP.json  (platform=windows)"
