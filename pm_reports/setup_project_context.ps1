param(
    [switch]$ShowProfiles,

    [Parameter(Mandatory=$false)]
    [string]$Project,

    [Parameter(Mandatory=$false)]
    [string]$ProjectKey,

    [string]$DisplayName,

    [ValidateSet('software_delivery','multi_workstream','managed_service')]
    [string]$Profile = 'software_delivery',

    [string]$ConfigFile = "$env:APPDATA\SensoneoAI\project_report_config.json"
)

$ErrorActionPreference = 'Stop'

if ($ShowProfiles) {
    Write-Host 'Available profiles:'
    Write-Host '- software_delivery (recommended default for most delivery projects)'
    Write-Host '- multi_workstream (two named workstreams plus shared scope/budget sections)'
    Write-Host '- managed_service (operations/support plus delivery)'
    exit 0
}

if (-not $Project -or -not $ProjectKey) {
    throw 'Missing required parameters. Pass -Project and -ProjectKey, or run with -ShowProfiles first.'
}

if (-not $DisplayName) { $DisplayName = $Project }

$dir = Split-Path -Parent $ConfigFile
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$templatePath = Join-Path $PSScriptRoot (Join-Path 'config_templates' ($Profile + '.json'))
if (-not (Test-Path $templatePath)) {
    throw "Profile template not found: $templatePath"
}

$config = Get-Content -Path $templatePath -Raw | ConvertFrom-Json
$config.project.name = $Project
$config.project.key = $ProjectKey
$config.project.display_name = $DisplayName
$config.profile = $Profile

$config | ConvertTo-Json -Depth 20 | Set-Content -Path $ConfigFile -Encoding UTF8

Write-Host "Saved project report config: $ConfigFile"
Write-Host "Project: $Project"
Write-Host "ProjectKey: $ProjectKey"
Write-Host "DisplayName: $DisplayName"
Write-Host "Profile: $Profile"
Write-Host ''
Write-Host 'Next step:'
Write-Host '- If you need project-specific weekly sections (for example TBS / DRS), edit the local JSON in %APPDATA% and keep it outside git.'
