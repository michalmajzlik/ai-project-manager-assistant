param(
    [string]$EnvFile,
    [string]$SecretFile = "$env:APPDATA\SensoneoAI\jira_secret.xml",
    [string]$PythonExe,
    [string]$ServerScript
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $EnvFile) { $EnvFile = Join-Path $scriptRoot '.env' }
if (-not $ServerScript) { $ServerScript = Join-Path $scriptRoot 'server.py' }
if (-not $PythonExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Users\Michal\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $PythonExe = $c; break }
    }
}

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
        }
    }
}

if (Test-Path $SecretFile) {
    $secret = Import-Clixml -Path $SecretFile
    if ($secret.JIRA_BASE_URL) { [Environment]::SetEnvironmentVariable('JIRA_BASE_URL', [string]$secret.JIRA_BASE_URL, 'Process') }
    if ($secret.JIRA_EMAIL) { [Environment]::SetEnvironmentVariable('JIRA_EMAIL', [string]$secret.JIRA_EMAIL, 'Process') }
    if ($secret.JIRA_BEARER_TOKEN) { [Environment]::SetEnvironmentVariable('JIRA_BEARER_TOKEN', [string]$secret.JIRA_BEARER_TOKEN, 'Process') }
    elseif ($secret.JIRA_API_TOKEN) { [Environment]::SetEnvironmentVariable('JIRA_API_TOKEN', [string]$secret.JIRA_API_TOKEN, 'Process') }
}

if (-not (Test-Path $PythonExe)) { throw "Python not found. Pass -PythonExe explicitly." }
if (-not (Test-Path $ServerScript)) { throw "Server script not found: $ServerScript" }

& $PythonExe $ServerScript
