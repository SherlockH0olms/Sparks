param(
    [ValidateSet('production', 'dev', 'demo')][string]$Mode = 'production',
    [ValidateRange(0,65535)][int]$ApiPort = 8000,
    [ValidateRange(0,65535)][int]$WebPort = 3000,
    [switch]$Open,
    [switch]$StrictPorts,
    [switch]$Plan
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv-win\Scripts\python.exe'
if ($Plan) {
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run project setup first.' }
    & $pythonPath (Join-Path $projectRoot 'scripts\run.py') --api-port $ApiPort --web-port $WebPort --plan
    exit $LASTEXITCODE
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & python -m venv (Join-Path $projectRoot '.venv-win')
    if ($LASTEXITCODE -ne 0) { throw 'Python environment could not be created.' }
    & $pythonPath -m pip install -r (Join-Path $projectRoot 'backend\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\node_modules'))) {
    Push-Location (Join-Path $projectRoot 'frontend')
    try { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' } }
    finally { Pop-Location }
}
$launchArgs = @((Join-Path $projectRoot 'scripts\run.py'), '--mode', $Mode, '--api-port', "$ApiPort", '--web-port', "$WebPort")
if ($Open) { $launchArgs += '--open' }
if ($StrictPorts) { $launchArgs += '--strict-ports' }
& $pythonPath @launchArgs
exit $LASTEXITCODE
