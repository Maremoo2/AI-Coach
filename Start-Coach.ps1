param([switch]$Demo)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$coachPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $coachPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
}
& $coachPython -m pip --disable-pip-version-check install -e .
if ($LASTEXITCODE -ne 0) { throw 'Could not install AI Coach.' }
if ($Demo) { & $coachPython -m ai_coach.server --demo --open }
else { & $coachPython -m ai_coach.server --open }
