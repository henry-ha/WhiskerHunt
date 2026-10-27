param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $InputPath)) {
    Write-Error "Log does not exist: $InputPath"
    exit 1
}
$all = [System.IO.File]::ReadAllLines($InputPath)
$patterns = 'HushFilament|HushHuntAR|HushGlb|filament|gltfio|AndroidRuntime|JNI DETECTED ERROR|Abort message|Fatal signal|SIGABRT|SIGSEGV|SIGBUS|F DEBUG|tombstone|backtrace:|runtime\.cc|Fatal Exception|native crash|ART Runtime|crash_dump|System\.IO\.InvalidDataException'
$included = New-Object 'System.Boolean[]' $all.Length
$matches = 0
for ($i=0; $i -lt $all.Length; $i++) {
    if ($all[$i] -match $patterns) {
        $matches++
        $start = [Math]::Max(0, $i - 15)
        $end = [Math]::Min($all.Length - 1, $i + 35)
        for ($j=$start; $j -le $end; $j++) { $included[$j] = $true }
    }
}
$output = New-Object 'System.Collections.Generic.List[string]'
$output.Add('Hush Hunt AR - native crash diagnostics (context before/after matching events)')
$output.Add(('Total log lines: {0}; matching lines: {1}' -f $all.Length, $matches))
$output.Add('Search for: JNI DETECTED ERROR, Abort message, F DEBUG, HushFilament STAGE, or the faulting native library.')
$output.Add('')
for ($i=0; $i -lt $all.Length; $i++) {
    if ($included[$i]) {
        $output.Add($all[$i])
        if ($output.Count -ge 10000) {
            $output.Add('--- Filtered output truncated at 10,000 lines: use the full log for additional details. ---')
            break
        }
    }
}
if ($matches -eq 0) $output.Add('No matching errors were found. Send the full log if the app crashed.')
[System.IO.File]::WriteAllLines($OutputPath, $output.ToArray(), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Saved: $OutputPath ($matches matching events)"
