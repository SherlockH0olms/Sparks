"""Exercise the real Windows migration functions with simulated process owners."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows workspace manager")
MANAGER = Path(__file__).resolve().parents[2] / "scripts" / "Open-LiveWorkspace.ps1"


@pytest.mark.parametrize("scenario", ["array-consumption", "stale-pids", "active-jobs"])
def test_legacy_migration_preserves_unrelated_and_active_services(tmp_path, scenario):
    runtime = tmp_path / ".runtime"
    runtime.mkdir()
    inspection = runtime / "legacy-instance-inspection.json"
    records = [
        {"Port": 3000, "ProcessId": 23000, "ProjectOwned": False},
        {"Port": 3007, "ProcessId": 23007, "ProjectOwned": True},
        {"Port": 8007, "ProcessId": 28007, "ProjectOwned": True},
        {"Port": 8008, "ProcessId": 28008, "ProjectOwned": True},
    ]
    inspection.write_text(json.dumps(records), encoding="utf-8")
    harness = tmp_path / "migration-test.ps1"
    harness.write_text(r'''
param([string]$Manager, [string]$Workspace, [string]$Scenario)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Manager, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'The workspace manager has invalid PowerShell syntax.' }
$functions = $ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst]}, $false)
foreach ($definition in $functions) { Invoke-Expression $definition.Extent.Text }
$taskRepoRoot = $Workspace
$script:stopped = [System.Collections.Generic.List[int]]::new()
function Get-WorkspaceListener([int]$Port) {
    if ($Scenario -eq 'stale-pids' -and $Port -eq 3007) { return 99999 }
    if ($Port -lt 8000) { return $Port + 20000 }
    return $Port + 20000
}
function Get-WorkspaceHealth([string]$BaseUrl) {
    $port = ([uri]$BaseUrl).Port
    $jobs = if ($Scenario -eq 'active-jobs' -and $port -eq 8008) { 1 } else { 0 }
    return [pscustomobject]@{version='2.0.0';fixture_environment=($port -ne 8008);workers=@{active_jobs=$jobs}}
}
function Stop-OwnedWorkspaceProcess([int]$ProcessId) { $script:stopped.Add($ProcessId) }
$blocked = $false
try { Retire-InspectedLegacyInstances } catch {
    if ($Scenario -ne 'active-jobs' -or $_.Exception.Message -notmatch 'active campaign') { throw }
    $blocked = $true
}
$path = Join-Path $Workspace '.runtime\legacy-instance-inspection.json'
$saved = Read-JsonFile $path
if ($Scenario -eq 'active-jobs') {
    if (-not $blocked -or $script:stopped.Count -ne 0 -or $saved -isnot [array]) {
        throw 'Active campaigns must block all retirement without consuming the inspection.'
    }
} else {
    $expected = if ($Scenario -eq 'stale-pids') { @(28007,28008) } else { @(23007,28007,28008) }
    if (($script:stopped -join ',') -ne ($expected -join ',')) { throw 'An owned service was skipped, or another application was stopped.' }
    if ($saved.completed -ne $true -or @($saved.processes).Count -ne 4) { throw 'The inspection must be consumed and retained for audit.' }
    $script:stopped.Clear()
    Retire-InspectedLegacyInstances
    if ($script:stopped.Count -ne 0) { throw 'A consumed inspection must never stop a reused PID.' }
}
''', encoding="utf-8")
    completed = subprocess.run(
        [shutil.which("powershell.exe"), "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(harness), "-Manager", str(MANAGER), "-Workspace", str(tmp_path),
         "-Scenario", scenario],
        capture_output=True, text=True, timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
