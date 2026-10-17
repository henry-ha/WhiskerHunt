# Whisker Hunt emergency read-only collection extraction.
# Does not modify or clear app data; does not deploy or install anything.
# Works for a debuggable Android build where `run-as` is authorised.
param([string]$Package = 'uk.whiskerhunt.mobile')
$ErrorActionPreference = 'Stop'
$adb = (Get-Command adb -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
if (-not $adb) {
  $candidates = @(
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    "${env:ProgramFiles(x86)}\Android\android-sdk\platform-tools\adb.exe",
    "$env:ProgramFiles\Android\android-sdk\platform-tools\adb.exe"
  )
  $adb = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $adb) { Write-Host 'ERROR: adb.exe was not found. Open Visual Studio Android SDK Manager or add platform-tools to PATH.' -ForegroundColor Red; exit 1 }
$devices = & $adb devices
$connected = @($devices | Where-Object { $_ -match '\sdevice\s*$' -and $_ -notmatch '^List of devices' })
if ($connected.Count -ne 1) { Write-Host 'Connect one unlocked phone, enable USB debugging, approve the USB prompt, then retry.' -ForegroundColor Yellow; $devices; exit 2 }
$check = & $adb shell run-as $Package pwd 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "ERROR: Android won't allow read-only access to $Package. This requires a debuggable build." -ForegroundColor Red
  $check; exit 3
}
$out = Join-Path (Get-Location) ("WhiskerHunt_Rescue_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $out -Force | Out-Null
Write-Host "Saving READ-ONLY copies to $out" -ForegroundColor Cyan

function Copy-AdbBinary([string[]]$arguments, [string]$path) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $adb
  $psi.Arguments = ($arguments -join ' ')
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $proc = [System.Diagnostics.Process]::Start($psi)
  $stream = [System.IO.File]::Create($path)
  try { $proc.StandardOutput.BaseStream.CopyTo($stream) }
  finally { $stream.Close() }
  $stderr = $proc.StandardError.ReadToEnd()
  $proc.WaitForExit()
  if ($proc.ExitCode -ne 0 -or (Get-Item $path).Length -eq 0) {
    Remove-Item $path -ErrorAction SilentlyContinue
    Write-Host "Not present or unreadable: $path" -ForegroundColor Yellow
    if ($stderr) { Write-Host $stderr }
    return $false
  }
  Write-Host "Saved $path ($((Get-Item $path).Length) bytes)" -ForegroundColor Green
  return $true
}
$names = @('whisker-hunt-state.json','whisker-hunt-state.json.bak','whisker-hunt-state.json.tmp')
foreach ($name in $names) {
  $target = Join-Path $out $name
  Copy-AdbBinary @('exec-out','run-as',$Package,'cat',("files/" + $name)) $target | Out-Null
}
# Optional raw archive of the app's private files and WebView/IndexedDB store.
# It may contain private photos and locations. Keep it local, not on public sharing sites.
$archive = Join-Path $out 'private-files-and-webview.tar'
Copy-AdbBinary @('exec-out','run-as',$Package,'tar','-cf','-','files','app_webview') $archive | Out-Null

foreach ($name in $names) {
  $path = Join-Path $out $name
  if (!(Test-Path $path)) { continue }
  try {
    $data = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $cats = @($data.cats).Count
    $virtual = @($data.cats | Where-Object { $_.virtual -eq $true }).Count
    $pins = @($data.cats | ForEach-Object { $_.sightings } | Where-Object { $null -ne $_.lat -and $null -ne $_.lng }).Count
    Write-Host "$name : $cats cats, $virtual virtual, $pins location pins" -ForegroundColor Cyan
  } catch { Write-Host "$name : present, but JSON could not be parsed" -ForegroundColor Yellow }
}
Write-Host 'Finished. NOTHING was changed on the phone.' -ForegroundColor Green
Write-Host 'Keep the entire rescue folder private and backed up. It can contain photos and location coordinates.' -ForegroundColor Yellow
