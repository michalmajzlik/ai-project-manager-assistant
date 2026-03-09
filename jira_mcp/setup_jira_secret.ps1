param(
    [string]$BaseUrl = "https://sensoneosk.atlassian.net",
    [string]$Email = "michal.majzlik@sensoneo.com",
    [switch]$UseBearer,
    [string]$SecretFile = "$env:APPDATA\SensoneoAI\jira_secret.xml"
)

$dir = Split-Path -Parent $SecretFile
if (-not (Test-Path $dir)) {
    New-Item -Path $dir -ItemType Directory -Force | Out-Null
}

if ($UseBearer) {
    $secure = Read-Host "Enter JIRA_BEARER_TOKEN" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }

    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "Bearer token cannot be empty."
    }

    [pscustomobject]@{
        JIRA_BASE_URL     = $BaseUrl
        JIRA_EMAIL        = $Email
        JIRA_BEARER_TOKEN = $token
        JIRA_API_TOKEN    = ""
    } | Export-Clixml -Path $SecretFile -Force
} else {
    $secure = Read-Host "Enter JIRA_API_TOKEN" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }

    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "API token cannot be empty."
    }

    [pscustomobject]@{
        JIRA_BASE_URL     = $BaseUrl
        JIRA_EMAIL        = $Email
        JIRA_BEARER_TOKEN = ""
        JIRA_API_TOKEN    = $token
    } | Export-Clixml -Path $SecretFile -Force
}

Write-Host "Saved encrypted Jira credentials to: $SecretFile"
Write-Host "Next run: powershell -ExecutionPolicy Bypass -File 'C:\Sensoneo AI\jira_mcp\run_jira_mcp.ps1'"
