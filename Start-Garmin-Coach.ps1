param([switch]$Login, [switch]$Sync, [switch]$Demo, [int]$Port = 8767)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$garminVenv = Join-Path $PSScriptRoot '.venv-garmin'
$isWindows = $env:OS -eq 'Windows_NT'
if ($isWindows) {
    $coachPython = Join-Path $garminVenv 'Scripts/python.exe'
    $pythonLauncher = 'py'
    $pythonArgs = @('-3.12')
} else {
    $coachPython = Join-Path $garminVenv 'bin/python'
    $pythonLauncher = 'python3.12'
    $pythonArgs = @()
}
if (-not (Test-Path -LiteralPath $coachPython)) {
    if (-not (Get-Command $pythonLauncher -ErrorAction SilentlyContinue)) {
        throw 'Python 3.12 må installeres først. Se docs/garmin.md.'
    }
    & $pythonLauncher @pythonArgs -m venv $garminVenv
    if ($LASTEXITCODE -ne 0) { throw 'Kunne ikke opprette Garmin-miljøet.' }
}
& $coachPython -m pip --disable-pip-version-check install -e '.[garmin]'
if ($LASTEXITCODE -ne 0) { throw 'Kunne ikke installere Garmin-avhengighetene.' }
if ($Login) { & $coachPython -m ai_coach.garmin --login }
elseif ($Sync) { & $coachPython -m ai_coach.garmin }
elseif ($Demo) { & $coachPython -m ai_coach.server --demo --port $Port --open }
else { & $coachPython -m ai_coach.server --port $Port --open }
