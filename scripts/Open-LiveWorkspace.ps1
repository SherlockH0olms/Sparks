# Open the English live workspace using available ports and an isolated release.
param(
    [string]$BuiltRelease = '',
    [ValidateRange(0,65535)][int]$ApiPort = 8008,
    [ValidateRange(0,65535)][int]$WebPort = 3002,
    [switch]$Plan
)
$ErrorActionPreference = 'Stop'
$taskRepoRoot = Split-Path -Parent $PSScriptRoot
$taskRuntime = Join-Path $taskRepoRoot '.runtime\english-preview-8008'
$taskPython = Join-Path $taskRepoRoot '.venv-win\Scripts\python.exe'
$taskLauncher = Join-Path $taskRepoRoot 'scripts\run.py'
$taskStatePath = Join-Path $taskRepoRoot '.runtime\live-workspace.json'

function Get-WorkspaceListener([int]$Port) {
    $pattern = '^\s*TCP\s+\S+:' + $Port + '\s+\S+\s+LISTENING\s+(\d+)\s*$'
    $line = netstat -ano -p TCP | Select-String $pattern | Select-Object -First 1
    if ($line) { return [int]$line.Matches[0].Groups[1].Value }
    return $null
}

function Get-WorkspaceHealth([string]$BaseUrl) {
    try { return Invoke-RestMethod ($BaseUrl.TrimEnd('/') + '/api/health') -TimeoutSec 2 }
    catch { return $null }
}

function Read-WorkspaceState {
    if (Test-Path -LiteralPath $taskStatePath) {
        try { return Get-Content -Raw -LiteralPath $taskStatePath | ConvertFrom-Json }
        catch { return $null }
    }
    return $null
}

function Test-OwnedBackend([int]$ProcessId, [int]$Port, $Health, $State) {
    # A fresh, random instance ID ties a saved launch record to the current listener.
    if ($State -and $State.source -eq $taskRepoRoot -and $State.runtime_dir -eq $taskRuntime -and
        $State.backend_pid -eq $ProcessId -and $State.api_port -eq $Port -and
        $State.instance_id -and $Health.instance_id -eq $State.instance_id) { return $true }
    # One-time migration of the original saved Granite workspace. A process name
    # or a generic AEGIS health response alone is never sufficient ownership proof.
    try {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId"
        $legacyPath = Join-Path $taskRepoRoot '.runtime\run_english_preview.py'
        if ($Port -eq 8008 -and $processInfo.CommandLine -match [regex]::Escape($legacyPath) -and
            $processInfo.CommandLine -match '\sapi(?:\s|$)' -and
            $processInfo.CommandLine -match '--api-port\s+8008(?:\s|$)' -and
            $processInfo.CommandLine -notmatch '--mode\s+demo') { return $true }
        $parentInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($processInfo.ParentProcessId)"
        if ($Port -eq 8008 -and $processInfo.CommandLine -match 'uvicorn\s+aegis_v2\.api:app' -and
            $parentInfo.CommandLine -match [regex]::Escape($taskLauncher) -and
            $parentInfo.CommandLine -match '--api-port\s+8008(?:\s|$)' -and
            $parentInfo.CommandLine -match '--mode\s+production') { return $true }
    } catch { }
    return $false
}

function Open-VerifiedWorkspace($State) {
    & node (Join-Path $taskRepoRoot 'scripts\verify-live-workspace.cjs') --base-url $State.platform_url --instance-id $State.instance_id
    if ($LASTEXITCODE -ne 0) { throw 'Live page validation failed. See .runtime\live-platform-verification.json.' }
    Remove-ObsoleteTurkishInterface $State.platform_url
    $taskNewline = [Environment]::NewLine
    $connectionText = "AEGIS LOOP / ENGLISH LIVE PLATFORM" + $taskNewline + $taskNewline + "Platform: $($State.platform_url)" + $taskNewline + "API documentation: $($State.api_url)/docs" + $taskNewline
    [IO.File]::WriteAllText((Join-Path $taskRepoRoot '.runtime\PLATFORM-URL.txt'), $connectionText)
    [IO.File]::WriteAllText((Join-Path $taskRepoRoot '.runtime\OPEN-PLATFORM.url'), "[InternetShortcut]" + $taskNewline + "URL=$($State.platform_url)" + $taskNewline)
    Write-Host ''
    Write-Host "English platform ready: $($State.platform_url)" -ForegroundColor Green
    Write-Host "API documentation: $($State.api_url)/docs"
    Write-Host 'Saved address: .runtime\PLATFORM-URL.txt'
    Start-Process $State.platform_url
}

function Remove-ObsoleteTurkishInterface([string]$CurrentUrl) {
    # Retire the obsolete in-memory interface only AFTER the English live release
    # passed validation. Documents, databases, evidence and English builds stay.
    $legacyPort = 3002
    if (([uri]$CurrentUrl).Port -eq $legacyPort) { return }
    try {
        $legacyPage = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$legacyPort/campaign" -TimeoutSec 2
        if ($legacyPage.Content -notmatch '<html[^>]*\blang="tr"') { return }
        $legacyHealth = Get-WorkspaceHealth "http://127.0.0.1:$legacyPort"
        if (-not $legacyHealth -or $legacyHealth.version -ne '2.0.0' -or $legacyHealth.workers.active_jobs -gt 0) { return }
        $legacyProcessId = Get-WorkspaceListener $legacyPort
        if (-not $legacyProcessId) { return }
        $legacyProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $legacyProcessId"
        $ownedNext = Join-Path $taskRepoRoot 'frontend\node_modules\next\dist\bin\next'
        if ($legacyProcess.Name -ne 'node.exe' -or $legacyProcess.CommandLine -notmatch [regex]::Escape($ownedNext)) {
            Write-Warning 'The obsolete Turkish interface could not be identified safely. Use the verified English address shown below.'
            return
        }
        Stop-Process -Id $legacyProcessId
        Write-Host 'The obsolete Turkish interface has been retired. Saved evidence is preserved.'
    } catch {
        Write-Warning 'The obsolete interface could not be retired automatically. Use the verified English address shown below.'
    }
}

if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run project setup first: .venv-win is missing.' }
if ($Plan) {
    & $taskPython $taskLauncher --api-port $ApiPort --web-port $WebPort --plan
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
# Serialize double-clicks so two launchers cannot restart the same workspace.
$taskLock = $null
try {
    try {
        $taskLock = [IO.File]::Open((Join-Path $taskRepoRoot '.runtime\live-workspace-startup.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch { throw 'Another AEGIS launch is already in progress. Let it finish before opening again.' }

    $taskNext = Join-Path $taskRepoRoot 'frontend\node_modules\next\dist\bin\next'
    $taskDistDir = $BuiltRelease
    if (-not $taskDistDir) {
        $buildManifest = Join-Path $taskRepoRoot '.runtime\current-production-build.json'
        if (Test-Path -LiteralPath $buildManifest) {
            $taskDistDir = (Get-Content -Raw -LiteralPath $buildManifest | ConvertFrom-Json).release
        }
    }
    if (-not $taskDistDir) { $taskDistDir = '.next-release-' + (Get-Date -Format 'yyyyMMdd-HHmmssfff') }
    if ($taskDistDir -notmatch '^\.next-release-[a-zA-Z0-9-]+$') { throw 'The release name is invalid.' }
    $env:AEGIS_NEXT_DIST_DIR = $taskDistDir
    $buildId = Join-Path $taskRepoRoot "frontend\$taskDistDir\BUILD_ID"
    if (-not (Test-Path -LiteralPath $buildId)) {
        if ($BuiltRelease) { throw 'The selected production release does not exist.' }
        Push-Location (Join-Path $taskRepoRoot 'frontend')
        try { & node $taskNext build; if ($LASTEXITCODE -ne 0) { throw 'Build failed; existing servers were left running.' } }
        finally { Pop-Location }
    }
    $taskState = Read-WorkspaceState
    if ($taskState -and $taskState.status -eq 'ready' -and $taskState.source -eq $taskRepoRoot -and
        $taskState.runtime_dir -eq $taskRuntime -and $taskState.release -eq $taskDistDir) {
        $taskHealth = Get-WorkspaceHealth $taskState.platform_url
        if ($taskHealth -and $taskState.instance_id -and $taskHealth.instance_id -eq $taskState.instance_id) {
            Open-VerifiedWorkspace $taskState
            exit 0
        }
    }

    # Retire only an identified API belonging to this saved workspace, never the
    # owner of an arbitrary web/API port. Existing unrelated servers stay running.
    $taskCandidatePorts = @(8008)
    if ($taskState -and $taskState.source -eq $taskRepoRoot -and $taskState.runtime_dir -eq $taskRuntime) {
        $taskCandidatePorts += [int]$taskState.api_port
    }
    foreach ($taskPort in ($taskCandidatePorts | Select-Object -Unique)) {
        $taskApiPid = Get-WorkspaceListener $taskPort
        if (-not $taskApiPid) { continue }
        $taskHealth = Get-WorkspaceHealth "http://127.0.0.1:$taskPort"
        if (-not $taskHealth -or $taskHealth.version -ne '2.0.0' -or $taskHealth.fixture_environment) { continue }
        if (-not (Test-OwnedBackend $taskApiPid $taskPort $taskHealth $taskState)) { continue }
        if ($taskHealth.workers.active_jobs -gt 0) { throw 'Pause active campaigns before updating the live workspace. Their records are preserved.' }
        Write-Host "Updating the verified AEGIS backend on port $taskPort."
        $taskOwnedProcess = Get-Process -Id $taskApiPid
        Stop-Process -Id $taskApiPid
        if (-not $taskOwnedProcess.WaitForExit(10000)) { throw 'The previous AEGIS backend did not stop. A duplicate worker was not started.' }
        if ($taskState -and $taskState.backend_pid -eq $taskApiPid) {
            # Its own supervisor shuts down its own frontend and publishes stopped
            # before the next supervisor writes this same state file.
            $taskSupervisor = Get-Process -Id $taskState.launcher_pid -ErrorAction SilentlyContinue
            if ($taskSupervisor -and -not $taskSupervisor.WaitForExit(15000)) { throw 'The previous AEGIS launcher is still shutting down. Run this launcher again shortly.' }
        }
    }
    $env:AEGIS_RUNTIME_DIR = $taskRuntime
    $env:AEGIS_DATABASE_URL = 'sqlite:///' + (Join-Path $taskRuntime 'audit.db').Replace('\', '/')
    $env:AEGIS_ALLOW_REMOTE_TARGETS = 'true'
    $taskLaunchArguments = @('"' + $taskLauncher + '"', '--mode', 'production',
        '--api-port', "$ApiPort", '--web-port', "$WebPort", '--dist-dir', $taskDistDir,
        '--state-file', '"' + $taskStatePath + '"')
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskLaunchArguments -WorkingDirectory $taskRepoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRepoRoot '.runtime\target-live-server.log') -RedirectStandardError (Join-Path $taskRepoRoot '.runtime\target-live-server-error.log') -PassThru
    for ($attempt = 0; $attempt -lt 240; $attempt++) {
        if ($taskProcess.HasExited) { throw 'The server exited. See .runtime\target-live-server-error.log.' }
        $taskNewState = Read-WorkspaceState
        if ($taskNewState -and $taskNewState.launcher_pid -eq $taskProcess.Id -and $taskNewState.status -eq 'ready') {
            Open-VerifiedWorkspace $taskNewState
            exit 0
        }
        Start-Sleep -Milliseconds 500
    }
    throw 'Startup timed out. See .runtime\target-live-server-error.log.'
} finally {
    if ($taskLock) { $taskLock.Dispose() }
}
