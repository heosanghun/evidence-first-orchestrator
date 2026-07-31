[CmdletBinding()]
param(
    [string]$Config = "$env:LOCALAPPDATA\EFO Monitor\config.json",
    [switch]$Stdout,
    [switch]$NoSubmit
)

$ErrorActionPreference = "Stop"

function Get-HexHmac {
    param(
        [Parameter(Mandatory = $true)][string]$Secret,
        [Parameter(Mandatory = $true)][string]$Payload
    )
    $encoding = [System.Text.UTF8Encoding]::new($false)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new(
        $encoding.GetBytes($Secret)
    )
    try {
        $bytes = $hmac.ComputeHash($encoding.GetBytes($Payload))
        return -join ($bytes | ForEach-Object { $_.ToString("x2") })
    }
    finally {
        $hmac.Dispose()
    }
}

if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
    throw "Config file does not exist: $Config"
}

$settings = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 |
    ConvertFrom-Json
$secretFile = [Environment]::ExpandEnvironmentVariables(
    [string]$settings.secret_file
)
if (-not (Test-Path -LiteralPath $secretFile -PathType Leaf)) {
    throw "Secret file does not exist: $secretFile"
}
$secret = (Get-Content -LiteralPath $secretFile -Raw -Encoding UTF8).Trim()
if ($secret.Length -lt 32) {
    throw "Local ingest secret must contain at least 32 characters."
}

$operatingSystem = Get-CimInstance Win32_OperatingSystem
$processors = Get-CimInstance Win32_Processor
$systemDisk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
if (-not $systemDisk) {
    throw "System drive C: was not found."
}

$cpuPercent = [double]((
    $processors | Measure-Object LoadPercentage -Average
).Average)
$memoryTotalGiB = [double]$operatingSystem.TotalVisibleMemorySize / 1MB
$memoryUsedGiB = (
    [double]$operatingSystem.TotalVisibleMemorySize -
    [double]$operatingSystem.FreePhysicalMemory
) / 1MB
$memoryPercent = if ($memoryTotalGiB -gt 0) {
    ($memoryUsedGiB / $memoryTotalGiB) * 100
} else { 0 }
$diskTotalGiB = [double]$systemDisk.Size / 1GB
$diskFreeGiB = [double]$systemDisk.FreeSpace / 1GB
$diskPercent = if ($diskTotalGiB -gt 0) {
    (1 - ($diskFreeGiB / $diskTotalGiB)) * 100
} else { 0 }
$uptimeSeconds = [math]::Max(
    0,
    [math]::Round(((Get-Date) - $operatingSystem.LastBootUpTime).TotalSeconds)
)

$payload = [ordered]@{
    schema_version = "1.0"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    collection_interval_seconds = [int]$settings.collection_interval_seconds
    device_alias = [string]$settings.device_alias
    cpu_percent = [math]::Round($cpuPercent, 1)
    memory = [ordered]@{
        used_gib = [math]::Round($memoryUsedGiB, 1)
        total_gib = [math]::Round($memoryTotalGiB, 1)
        percent = [math]::Round($memoryPercent, 1)
    }
    disk = [ordered]@{
        free_gib = [math]::Round($diskFreeGiB, 1)
        total_gib = [math]::Round($diskTotalGiB, 1)
        percent = [math]::Round($diskPercent, 1)
    }
    uptime_seconds = [double]$uptimeSeconds
    process_count = [int](Get-Process).Count
}

$body = $payload | ConvertTo-Json -Depth 4 -Compress
if ($Stdout) {
    $body
}
if ($NoSubmit) {
    return
}

$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
$signature = Get-HexHmac -Secret $secret -Payload "$timestamp.$body"
$headers = @{
    "x-efo-timestamp" = $timestamp
    "x-efo-signature" = "sha256=$signature"
}
$response = Invoke-RestMethod -Uri ([string]$settings.endpoint) `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.UTF8Encoding]::new($false).GetBytes($body))

$response | ConvertTo-Json -Depth 4 -Compress
