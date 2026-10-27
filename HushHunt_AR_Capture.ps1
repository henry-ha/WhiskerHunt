# Hush Hunt v3.10.36: safe Android native crash-log collection for Windows PowerShell 5.1.
# Collects logs only; does not build, install, modify, or uninstall the app.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$script:logDir = $PSScriptRoot
$script:status = $null

function Say([string]$message) {
    Write-Host $message
    if ($script:status) { Add-Content -LiteralPath $script:status -Value $message -Encoding UTF8 }
}
function Get-LogDirectory {
    $dirs = @($PSScriptRoot)
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $dirs += (Join-Path $env:USERPROFILE 'Desktop')
    }
    $dirs += $env:TEMP
    foreach ($dir in $dirs) {
        if ([string]::IsNullOrWhiteSpace($dir)) { continue }
        try {
            if (-not (Test-Path -LiteralPath $dir -PathType Container)) { continue }
            $probe = Join-Path $dir 'HushHunt_AR_Write_Test.tmp'
            [System.IO.File]::WriteAllText($probe, 'test')
            Remove-Item -LiteralPath $probe -Force
            return $dir
        } catch { }
    }
    throw 'No writable log folder found.'
}
function Find-Adb {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    try {
        $command = Get-Command 'adb.exe' -ErrorAction SilentlyContinue
        if ($command) { $candidates.Add($command.Source) }
    } catch { }
    foreach ($sdk in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, $env:ANDROIDSDKROOT)) {
        if (-not [string]::IsNullOrWhiteSpace($sdk)) {
            $candidates.Add((Join-Path $sdk 'platform-tools\adb.exe'))
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'))
        $candidates.Add((Join-Path $env:LOCALAPPDATA 'Xamarin\Mono for Android\AndroidSDK\platform-tools\adb.exe'))
    }
    if (-not [string]::IsNullOrWhiteSpace(${env:ProgramFiles(x86)})) {
        $candidates.Add((Join-Path ${env:ProgramFiles(x86)} 'Android\android-sdk\platform-tools\adb.exe'))
        $candidates.Add((Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\Community\Common7\IDE\Extensions\Xamarin.VisualStudio\Android\platform-tools\adb.exe'))
    }
    if (-not [string]::IsNullOrWhiteSpace($env:ProgramFiles)) {
        $candidates.Add((Join-Path $env:ProgramFiles 'Android\android-sdk\platform-tools\adb.exe'))
    }
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $candidates.Add((Join-Path $env:USERPROFILE 'AppData\Local\Android\Sdk\platform-tools\adb.exe'))
    }
    # Visual Studio Android SDK paths can also be registered with Windows.
    foreach ($regPath in @('HKLM:\SOFTWARE\WOW6432Node\Android SDK Tools', 'HKLM:\SOFTWARE\Android SDK Tools')) {
        try {
            $property = Get-ItemProperty -LiteralPath $regPath -ErrorAction Stop
            if ($property.Path) { $candidates.Add((Join-Path $property.Path 'platform-tools\adb.exe')) }
        } catch { }
    }
    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }
    return $null
}
function Filter-Log([string]$src, [string]$dst) {
    $lines = [System.IO.File]::ReadAllLines($src)
    $pattern = '(?i)HushFilament|HushHuntAR|FilamentOverlay|filament|gltfio|AndroidRuntime|JNI DETECTED|Abort message|FATAL EXCEPTION|Fatal signal|SIGABRT|SIGSEGV|SIGBUS|DEBUG\s*:|backtrace:|tombstone|libfilament|libgltfio|runtime\.cc|InvalidDataException|abort\(|crash_dump|skermunt\.mobile|skermunt\.mobile'
    $include = New-Object 'System.Boolean[]' $lines.Length
    $found = 0
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -match $pattern) {
            $found++
            $start = [Math]::Max(0, $i - 25)
            $end = [Math]::Min($lines.Length - 1, $i + 75)
            for ($j = $start; $j -le $end; $j++) { $include[$j] = $true }
        }
    }
    $result = New-Object 'System.Collections.Generic.List[string]'
    $result.Add('Hush Hunt AR - Filtered native crash log')
    $result.Add(('Full log lines: {0}; matching events: {1}' -f $lines.Length, $found))
    $result.Add('If the cause is missing, send the full log or review it in Android Logcat. Check for JNI DETECTED ERROR, Abort message, or crash_dump backtrace.')
    $result.Add('')
    $max = 15000
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($include[$i]) {
            $result.Add($lines[$i])
            if ($result.Count -gt $max) { $result.Add('--- More data in full log ---'); break }
        }
    }
    if ($found -eq 0) { $result.Add('No matching crash lines found. The app may not have crashed during the capture interval.') }
    [System.IO.File]::WriteAllLines($dst, $result.ToArray(), (New-Object System.Text.UTF8Encoding($false)))
}
function Capture-Log([string]$adb, [string]$dst) {
    $bufferArgs = @('logcat','-d','-v','threadtime','-b','main','-b','system','-b','crash')
    & $adb @bufferArgs 2>&1 | Out-File -LiteralPath $dst -Encoding UTF8 -Width 4096
    if ($LASTEXITCODE -ne 0) { throw ('adb logcat failed with exit code ' + $LASTEXITCODE) }
    if (-not (Test-Path -LiteralPath $dst) -or (Get-Item -LiteralPath $dst).Length -eq 0) { throw 'adb returned no log data.' }
}

try {
    $script:logDir = Get-LogDirectory
    $script:status = Join-Path $script:logDir 'HushHunt_Logger_Status.txt'
    Set-Content -LiteralPath $script:status -Value 'Hush Hunt crash logger v2 - diagnostic status' -Encoding UTF8
    $filtered = Join-Path $script:logDir 'HushHunt_AR_Log_Filtered.txt'
    $full = Join-Path $script:logDir 'HushHunt_AR_Log_Full.txt'
    $existingFull = Join-Path $script:logDir 'HushHunt_AR_Log_Existing_Full.txt'
    $existingFiltered = Join-Path $script:logDir 'HushHunt_AR_Log_Existing_Filtered.txt'
    # Create a visible result even if ADB isn't found or the phone is disconnected.
    Set-Content -LiteralPath $filtered -Value 'Logger started, but a new crash has not been captured yet. See HushHunt_Logger_Status.txt.' -Encoding UTF8
    Say ('Files will be saved in: ' + $script:logDir)
    Say 'Searching for Android Debug Bridge (adb.exe)...'
    $adb = Find-Adb
    if (-not $adb) {
        Say 'ERROR: adb.exe not found. Open Visual Studio > Tools > Android > Android SDK Manager, locate your Android SDK folder and its platform-tools\adb.exe.'
        Say 'You can also run this command in Windows CMD: where /r "C:\Program Files (x86)\Android" adb.exe'
        throw 'ADB_NOT_FOUND'
    }
    Say ('ADB found: ' + $adb)
    & $adb start-server | Out-Null
    $devicesText = (& $adb devices -l 2>&1 | Out-String)
    Say $devicesText
    if ($devicesText -notmatch '(?m)^[^\r\n\s]+\s+device\b') {
        throw 'NO_AUTHORISED_DEVICE: Connect OnePlus via USB and accept the USB debugging authorisation on the phone.'
    }
    Say 'Taking a snapshot of existing logs (nothing has been cleared yet)...'
    Capture-Log $adb $existingFull
    Filter-Log $existingFull $existingFiltered
    Say 'Existing logs saved: HushHunt_AR_Log_Existing_Filtered.txt'
    Write-Host ''
    Write-Host 'The previous crash may already be in the EXISTING filtered log.' -ForegroundColor Yellow
    [void](Read-Host 'Press Enter to start a NEW capture (older logs have already been saved)')
    & $adb logcat -c 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Failed to clear logcat. Existing logs are safe.' }
    Write-Host ''
    Write-Host 'On your OnePlus: Open Hush Hunt > 3D Safari > Domestic Shorthair.' -ForegroundColor Cyan
    Write-Host 'If it crashes, return to this window.'
    [void](Read-Host 'Press Enter AFTER reproducing the crash')
    Capture-Log $adb $full
    Filter-Log $full $filtered
    Say 'SUCCESS: New filtered crash log created: HushHunt_AR_Log_Filtered.txt'
    Say 'New full log created: HushHunt_AR_Log_Full.txt'
    Say 'Send the filtered log after reviewing it for sensitive information.'
} catch {
    $msg = 'ERROR: ' + $_.Exception.Message
    Write-Host $msg -ForegroundColor Red
    if ($script:status) { Add-Content -LiteralPath $script:status -Value $msg -Encoding UTF8 }
    if ($script:logDir) {
        try { Add-Content -LiteralPath (Join-Path $script:logDir 'HushHunt_AR_Log_Filtered.txt') -Value $msg -Encoding UTF8 } catch { }
    }
} finally {
    Write-Host ''
    Write-Host ('Status / logs folder: ' + $script:logDir) -ForegroundColor Green
    [void](Read-Host 'Press Enter to return to the launcher')
}
