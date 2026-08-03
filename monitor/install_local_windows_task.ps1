[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Config = "$env:LOCALAPPDATA\EFO Monitor\config.json"
)

$ErrorActionPreference = "Stop"
$collector = Join-Path $RepositoryRoot "monitor\collect_local_windows.ps1"
if (-not (Test-Path -LiteralPath $collector -PathType Leaf)) {
    throw "Collector does not exist: $collector"
}
if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
    throw "Config does not exist: $Config"
}

$taskName = "EFO Local PC Monitor"
$arguments = @(
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$collector`"",
    "-Config", "`"$Config`""
) -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 2)
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Signed read-only EFO local PC telemetry" `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Get-ScheduledTask -TaskName $taskName |
    Select-Object TaskName, State, Description
