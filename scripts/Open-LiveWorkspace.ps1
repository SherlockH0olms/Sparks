# One entry point for the current English platform and its persistent workspace.
param(
    [string]$BuiltRelease = '',
    [ValidateRange(0,65535)][int]$ApiPort = 8008,
    [ValidateRange(0,65535)][int]$WebPort = 3002,
    [switch]$Restart,
    [switch]$Plan
)
$ErrorActionPreference = 'Stop'
$taskRepoRoot = Split-Path -Parent $PSScriptRoot
$taskRuntime = Join-Path $taskRepoRoot '.runtime\english-preview-8008'
$taskPython = Join-Path $taskRepoRoot '.venv-win\Scripts\python.exe'
$taskLauncher = Join-Path $taskRepoRoot 'scripts\run.py'
$taskStatePath = Join-Path $taskRepoRoot '.runtime\live-workspace.json'
$taskAddressPath = Join-Path $taskRepoRoot '.runtime\live-workspace-address.json'
$taskHistoryDir = Join-Path $taskRepoRoot '.runtime\live-instances'

function Read-JsonFile([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        try { return Get-Content -Raw -Encoding UTF8 -LiteralPath $Path | ConvertFrom-Json }
        catch { }
    }
    return $null
}
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
function Get-KnownWorkspaceStates {
    $states = @(Read-JsonFile $taskStatePath)
    if (Test-Path -LiteralPath $taskHistoryDir) {
        foreach ($file in (Get-ChildItem -LiteralPath $taskHistoryDir -Filter '*.json' -File)) {
            $states += Read-JsonFile $file.FullName
        }
    }
    return @($states | Where-Object { $_ -and $_.source -eq $taskRepoRoot -and $_.runtime_dir -eq $taskRuntime -and $_.instance_id } |
        Sort-Object created_at -Descending | Group-Object instance_id | ForEach-Object { $_.Group[0] })
}
function Test-OwnedInstance($State, $Health) {
    # The API's random identity remains valid across Windows Python redirectors.
    return $State -and $Health -and $State.source -eq $taskRepoRoot -and
        $State.runtime_dir -eq $taskRuntime -and $State.instance_id -and
        $Health.instance_id -eq $State.instance_id -and $Health.version -eq '2.0.0' -and
        -not $Health.fixture_environment
}
function Stop-OwnedWorkspaceProcess([int]$ProcessId) {
    # Every caller must first prove workspace ownership and check active jobs.
    & taskkill.exe /PID $ProcessId /F | Out-Host
    if ($LASTEXITCODE -ne 0 -and (Test-ProcessRunning $ProcessId)) {
        throw "Windows could not stop the verified AEGIS process $ProcessId."
    }
}
function Test-ProcessRunning([int]$ProcessId) {
    $rows = & tasklist.exe /FI "PID eq $ProcessId" /FO CSV /NH
    return [bool]($rows | Select-String ('^"[^"]+","' + $ProcessId + '",'))
}
function Wait-WorkspaceSupervisor([int]$ProcessId) {
    if ($ProcessId -le 0) { return }
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if (-not (Test-ProcessRunning $ProcessId)) { return }
        Start-Sleep -Milliseconds 250
    }
    throw 'The previous workspace supervisor is still closing. A second backend was not started.'
}
function Retire-KnownWorkspaceInstances($States) {
    $owned = @()
    # Check all jobs before stopping any service.
    foreach ($state in $States) {
        $health = Get-WorkspaceHealth $state.api_url
        if (-not (Test-OwnedInstance $state $health)) { continue }
        if ($health.workers.active_jobs -gt 0) {
            throw 'An active campaign is running. Pause it before updating; its checkpoint and evidence are preserved.'
        }
        $listener = Get-WorkspaceListener ([int]$state.api_port)
        if (-not $listener) { throw 'A known workspace API could not be identified on its recorded port.' }
        $webHealth = Get-WorkspaceHealth $state.platform_url
        $webPid = if ($webHealth -and $webHealth.instance_id -eq $state.instance_id) { Get-WorkspaceListener ([int]$state.web_port) } else { $null }
        $owned += [PSCustomObject]@{ State=$state; ApiPid=$listener; WebPid=$webPid }
    }
    foreach ($item in $owned) {
        Write-Host 'Updating the saved AEGIS workspace.'
        Stop-OwnedWorkspaceProcess $item.ApiPid
        Wait-WorkspaceSupervisor ([int]$item.State.launcher_pid)
        if ($item.WebPid -and (Get-WorkspaceListener ([int]$item.State.web_port)) -eq $item.WebPid) {
            Stop-OwnedWorkspaceProcess $item.WebPid
        }
    }
}
function Retire-InspectedLegacyInstances {
    # A one-time migration uses the process ownership inspection already approved.
    # Stale PID records are consumed afterwards and never reused for later launches.
    $path = Join-Path $taskRepoRoot '.runtime\legacy-instance-inspection.json'
    $inspection = Read-JsonFile $path
    if (-not $inspection) { return }
    # A legacy inspection is an array: PowerShell expands .completed into an
    # array of nulls, which is truthy. Check the completion flag only on objects.
    if ($inspection -isnot [array] -and $inspection.completed -eq $true) { return }
    $records = if ($inspection -is [array]) { @($inspection) } else { @($inspection.processes) }
    $plans = @()
    foreach ($record in $records) {
        if (-not $record.ProjectOwned -or $record.Port -notin @(3007,8007,8008)) { continue }
        $pidNow = Get-WorkspaceListener ([int]$record.Port)
        if ($pidNow -ne $record.ProcessId) { continue }
        $health = Get-WorkspaceHealth "http://127.0.0.1:$($record.Port)"
        if (-not $health -or $health.version -ne '2.0.0') { continue }
        if ($health.workers.active_jobs -gt 0) { throw 'A legacy workspace has an active campaign. Pause it before updating.' }
        if ($record.Port -in @(3007,8007) -and -not $health.fixture_environment) { continue }
        $plans += [int]$pidNow
    }
    foreach ($processId in $plans) { Stop-OwnedWorkspaceProcess $processId }
    [IO.File]::WriteAllText($path, (@{completed=$true;processes=@($records)} | ConvertTo-Json -Depth 8))
}
function Publish-VerifiedWorkspace($State) {
    & node (Join-Path $taskRepoRoot 'scripts\verify-live-workspace.cjs') --base-url $State.platform_url --instance-id $State.instance_id
    if ($LASTEXITCODE -ne 0) { throw 'Page validation failed. See .runtime\live-platform-verification.json.' }
    [IO.File]::WriteAllText($taskAddressPath, ($State | ConvertTo-Json -Depth 8))
    $nl = [Environment]::NewLine
    [IO.File]::WriteAllText((Join-Path $taskRepoRoot '.runtime\PLATFORM-URL.txt'),
        "AEGIS LOOP / ENGLISH LIVE PLATFORM" + $nl + $nl + "Platform: $($State.platform_url)" + $nl + "API documentation: $($State.api_url)/docs" + $nl)
    [IO.File]::WriteAllText((Join-Path $taskRepoRoot '.runtime\OPEN-PLATFORM.url'),
        "[InternetShortcut]" + $nl + "URL=$($State.platform_url)" + $nl)
    Write-Host ''
    Write-Host "AEGIS ready: $($State.platform_url)" -ForegroundColor Green
    Start-Process $State.platform_url
}
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run project setup first: .venv-win is missing.' }
if ($Plan) {
    & $taskPython $taskLauncher --api-port $ApiPort --web-port $WebPort --plan
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
New-Item -ItemType Directory -Path $taskHistoryDir -Force | Out-Null
$taskLock = $null
try {
    try { $taskLock = [IO.File]::Open((Join-Path $taskRepoRoot '.runtime\live-workspace-startup.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { throw 'AEGIS is already starting. Let that launch finish; another server was not started.' }
    $manifest = Read-JsonFile (Join-Path $taskRepoRoot '.runtime\current-production-build.json')
    # Old shortcuts with an embedded release also resolve to the current manifest.
    $taskDistDir = if ($manifest) { $manifest.release } elseif ($BuiltRelease) { $BuiltRelease } else { $null }
    if (-not $taskDistDir) { throw 'Build the project first: .venv-win\Scripts\python.exe scripts\build-production.py' }
    if ($taskDistDir -notmatch '^\.next-release-[a-zA-Z0-9-]+$') { throw 'The production artifact name is invalid.' }
    $taskArtifact = Join-Path $taskRepoRoot "frontend\$taskDistDir"
    if (-not (Test-Path -LiteralPath (Join-Path $taskArtifact 'BUILD_ID'))) { throw 'The production artifact is missing. Run the project build.' }
    $taskIndex = [IO.File]::ReadAllText((Join-Path $taskArtifact 'server\app\index.html'))
    if ($taskIndex -notmatch '<html[^>]*\blang="en"') { throw 'The production artifact must have an English interface.' }
    if ($manifest -and (Get-Content -Raw -LiteralPath (Join-Path $taskArtifact 'BUILD_ID')).Trim() -ne $manifest.build_id) { throw 'The production manifest and artifact do not match.' }
    $taskStates = Get-KnownWorkspaceStates
    $taskAddress = Read-JsonFile $taskAddressPath
    if (-not $taskAddress) {
        $textPath = Join-Path $taskRepoRoot '.runtime\PLATFORM-URL.txt'
        if (Test-Path -LiteralPath $textPath) {
            $text = [IO.File]::ReadAllText($textPath)
            $webMatch = [regex]::Match($text, 'Platform:\s*(http://127\.0\.0\.1:\d+/)')
            $apiMatch = [regex]::Match($text, 'API documentation:\s*(http://127\.0\.0\.1:\d+)/docs')
            if ($webMatch.Success -and $apiMatch.Success) {
                $taskAddress = [PSCustomObject]@{web_port=([uri]$webMatch.Groups[1].Value).Port;api_port=([uri]$apiMatch.Groups[1].Value).Port}
            }
        }
    }
    if ($taskAddress) {
        if (-not $PSBoundParameters.ContainsKey('ApiPort')) { $ApiPort = [int]$taskAddress.api_port }
        if (-not $PSBoundParameters.ContainsKey('WebPort')) { $WebPort = [int]$taskAddress.web_port }
    }
    foreach ($state in $taskStates) {
        if ($state.release -ne $taskDistDir -or $state.web_port -ne $WebPort -or $state.api_port -ne $ApiPort) { continue }
        $health = Get-WorkspaceHealth $state.platform_url
        if (-not $Restart -and (Test-OwnedInstance $state $health) -and $health.managed_workspace -and $health.workspace_release -eq $taskDistDir) {
            Retire-KnownWorkspaceInstances @($taskStates | Where-Object { $_.instance_id -ne $state.instance_id })
            Retire-InspectedLegacyInstances
            Publish-VerifiedWorkspace $state
            exit 0
        }
    }
    Retire-KnownWorkspaceInstances $taskStates
    Retire-InspectedLegacyInstances
    $env:AEGIS_RUNTIME_DIR = $taskRuntime
    $env:AEGIS_DATABASE_URL = 'sqlite:///' + (Join-Path $taskRuntime 'audit.db').Replace('\', '/')
    $env:AEGIS_ALLOW_REMOTE_TARGETS = 'true'
    $env:AEGIS_MANAGED_WORKSPACE = 'true'
    $env:AEGIS_NEXT_DIST_DIR = $taskDistDir
    $taskLaunchId = [guid]::NewGuid().ToString('N')
    $taskArguments = @('"' + $taskLauncher + '"', '--mode', 'production', '--api-port', "$ApiPort", '--web-port', "$WebPort",
        '--dist-dir', $taskDistDir, '--state-file', '"' + $taskStatePath + '"', '--launch-id', $taskLaunchId)
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory $taskRepoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRepoRoot '.runtime\target-live-server.log') -RedirectStandardError (Join-Path $taskRepoRoot '.runtime\target-live-server-error.log') -PassThru
    for ($attempt = 0; $attempt -lt 240; $attempt++) {
        $state = Read-JsonFile $taskStatePath
        if ($state -and $state.launch_id -eq $taskLaunchId) {
            if ($state.status -eq 'ready') { Publish-VerifiedWorkspace $state; exit 0 }
            if ($state.status -in @('failed','stopped')) { throw 'AEGIS could not start. See .runtime\target-live-server-error.log.' }
        }
        if ($taskProcess.HasExited) { throw 'AEGIS exited. See .runtime\target-live-server-error.log.' }
        Start-Sleep -Milliseconds 500
    }
    throw 'AEGIS did not become ready. See .runtime\target-live-server-error.log.'
} finally {
    if ($taskLock) { $taskLock.Dispose() }
}
