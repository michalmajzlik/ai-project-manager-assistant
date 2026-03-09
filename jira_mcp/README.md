# Local Jira MCP Server

## First-time setup (new machine or first run)
Run these commands from this folder (`jira_mcp`):

1. Save encrypted Jira token (per Windows user):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_jira_secret.ps1 -BaseUrl 'https://sensoneosk.atlassian.net' -Email '<your-email>'
```

2. Install autostart + heartbeat and start now:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1 -RunNow
```

After this, Jira MCP starts automatically on login and is kept alive by heartbeat.

## Tools
- `jira_search`: run JQL and return issue list with key metadata
- `jira_get_issue`: fetch one ticket detail (description + optional comments)

## Token storage
Token is intentionally not in workspace.
It is stored encrypted at:
- `%APPDATA%\SensoneoAI\jira_secret.xml`

## Manual run

```powershell
powershell -ExecutionPolicy Bypass -File .\run_jira_mcp.ps1
```

## Uninstall

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_tasks.ps1
```

## Move to another PC
1. Copy `jira_mcp` folder.
2. Run first-time setup steps above.

Notes:
- Scheduled tasks are OS objects and do not transfer by folder copy.
- Secret file is encrypted per Windows user profile and should be recreated on target machine.
