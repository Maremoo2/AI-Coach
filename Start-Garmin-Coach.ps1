param([switch]$Login, [switch]$Sync, [switch]$Demo, [int]$Port = 8767)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$coachPython = Join-Path $PSScriptRoot '.venv-garmin\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $coachPython)) {
    Write-Host 'Python 3.12 og Garmin-miljø må installeres først. Se docs/garmin.md.'
    exit 1
}
if ($Login) { & $coachPython -m ai_coach.garmin --login }
elseif ($Sync) { & $coachPython -m ai_coach.garmin }
elseif ($Demo) { & $coachPython -m ai_coach.server --demo --port $Port --open }
else { & $coachPython -m ai_coach.server --port $Port --open }
