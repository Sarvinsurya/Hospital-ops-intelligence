# Hospital Operations Intelligence System - Windows PowerShell launcher
# Run:  ./start.ps1   (you may need: Set-ExecutionPolicy -Scope Process Bypass)
Set-Location -Path $PSScriptRoot

$py = $null
foreach ($c in @("py -3.12", "py -3.11", "py -3", "python")) {
    $exe = $c.Split(" ")[0]
    if (Get-Command $exe -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Host "Python 3 not found. Install Python 3.12 from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

Write-Host "Using $py to launch..." -ForegroundColor Cyan
$parts = $py.Split(" ")
if ($parts.Count -gt 1) {
    & $parts[0] $parts[1] launch.py $args
} else {
    & $parts[0] launch.py $args
}
