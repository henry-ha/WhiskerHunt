# Hush Hunt v3.10.60d: non-destructive Debug signing and deployment recovery.
# No project/GLB files are modified. No app is uninstalled.
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$project = 'E:\inetpub\wwwroot\WhiskerHunt\WhiskerHunt\WhiskerHunt.csproj'
$package = 'uk.whiskerhunt.mobile'
$targetFramework = 'net10.0-android'
$configuration = 'Debug'

function Fail([string]$message) { Write-Host "FAILED: $message" -ForegroundColor Red; exit 1 }
function Locate-Command([string]$name, [string]$relativePath) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $roots = @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, "$env:LOCALAPPDATA\Android\Sdk", 'C:\Program Files (x86)\Android\android-sdk', 'C:\Android\android-sdk')
  foreach ($root in $roots) {
    if (-not $root) { continue }
    $candidate = Join-Path $root $relativePath
    if (Test-Path -LiteralPath $candidate) { return $candidate }
  }
  return $null
}
function Locate-ApkSigner {
  $cmd = Get-Command 'apksigner.bat' -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $roots = @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, "$env:LOCALAPPDATA\Android\Sdk", 'C:\Program Files (x86)\Android\android-sdk', 'C:\Android\android-sdk')
  foreach ($root in $roots) {
    if (-not $root) { continue }
    $toolRoot = Join-Path $root 'build-tools'
    if (-not (Test-Path -LiteralPath $toolRoot)) { continue }
    $candidates = @(Get-ChildItem -LiteralPath $toolRoot -Filter 'apksigner.bat' -File -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
    if ($candidates.Count -gt 0) { return $candidates[0].FullName }
  }
  return $null
}

if (-not (Test-Path -LiteralPath $project)) { Fail "Project not found: $project" }
$dotnet = Get-Command 'dotnet.exe' -ErrorAction SilentlyContinue
if (-not $dotnet) { Fail 'dotnet.exe not found in PATH; open from your Visual Studio Developer PowerShell or set PATH.' }
$adb = Locate-Command 'adb.exe' 'platform-tools\adb.exe'
if (-not $adb) { Fail 'adb.exe not found. Install Android SDK platform-tools or add adb to PATH.' }
$signer = Locate-ApkSigner
if (-not $signer) { Fail 'apksigner.bat not found in Android SDK build-tools. Cannot prove APK is signed.' }

Write-Host 'HUSH HUNT v3.10.60d - DEBUG APK SIGNING RECOVERY' -ForegroundColor Cyan
Write-Host "Project: $project"
Write-Host 'This tool never uninstalls Hush Hunt or changes source/GLB files.'
$binPath = Join-Path (Split-Path -Parent $project) "bin\$configuration\$targetFramework"

if (-not $CheckOnly) {
  Write-Host '\nBuilding a self-contained DEBUG APK and explicitly running SignAndroidPackage...' -ForegroundColor Cyan
  $buildArgs = @(
    'build', $project, '-c', $configuration, '-f', $targetFramework, '-t:SignAndroidPackage',
    '-p:AndroidKeyStore=false',
    '-p:AndroidPackageFormats=apk',
    '-p:AndroidUseApkSigner=true',
    '-p:EmbedAssembliesIntoApk=true',
    '-p:AndroidEnableFastDeployment=false'
  )
  & $dotnet.Source @buildArgs
  if ($LASTEXITCODE -ne 0) { Fail 'Signing build target failed. Share the complete command output.' }
}
if (-not (Test-Path -LiteralPath $binPath)) { Fail "APK output folder missing: $binPath" }
$apkCandidates = @(Get-ChildItem -LiteralPath $binPath -Filter '*-Signed.apk' -File -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
if ($apkCandidates.Count -eq 0) { Fail 'No -Signed.apk found. SignAndroidPackage target did not produce a signed APK.' }
$apk = $apkCandidates[0]
Write-Host "\nCandidate: $($apk.FullName)" -ForegroundColor Cyan
Write-Host "Modified:  $($apk.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host 'Verifying cryptographic signature with Android SDK apksigner...'
& $signer verify --verbose --print-certs $apk.FullName
if ($LASTEXITCODE -ne 0) { Fail 'apksigner verification failed: DO NOT install this APK.' }
Write-Host 'APK SIGNATURE VERIFIED' -ForegroundColor Green
if ($CheckOnly) {
  Write-Host 'CHECK ONLY: no APK was built or installed.'
  exit 0
}

$deviceLines = @(& $adb devices | Where-Object { $_ -match '^\S+\s+device\s*$' })
if ($deviceLines.Count -ne 1) { Fail "Expected exactly one authorised Android device; found $($deviceLines.Count). Run 'adb devices' and check USB debugging." }
Write-Host '\nInstalling the VERIFIED signed APK as an update (adb install -r)...' -ForegroundColor Cyan
Write-Host 'This does not uninstall the existing app or intentionally erase its data.'
& $adb install -r $apk.FullName
if ($LASTEXITCODE -ne 0) {
  Fail "ADB install failed. If the output says UPDATE_INCOMPATIBLE or INCONSISTENT_CERTIFICATES, stop and preserve the current app/data; DO NOT uninstall automatically."
}
Write-Host 'INSTALL SUCCEEDED' -ForegroundColor Green
Write-Host '\nLaunching Hush Hunt...' -ForegroundColor Cyan
& $adb shell monkey -p $package -c android.intent.category.LAUNCHER 1
if ($LASTEXITCODE -ne 0) { Write-Host 'Install passed, but automatic launch failed. You can open Hush Hunt manually.' -ForegroundColor Yellow }
Write-Host 'DONE. Test Live Petting 2.0; keep an eye on the crash/gesture status.' -ForegroundColor Green
