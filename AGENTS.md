# AGENTS.md

## Weekly Capacity Rule (Project Variable)
For the `Capacity and workload (MD)` section in weekly reports, use this Jira JQL template:

`project = {project_key} and issuetype = Epic and status = Closed and status CHANGED TO Closed AFTER -90d`

Implementation notes:
- Scope only issues with `issuetype = Epic`.
- Track `Refined Estimation MDs` (planned) vs `Time Spent MDs` (consumed).
- Burn formula: `% Burn = Consumed / Planned`.
- Capacity table order: `Epic | Ticket name | Status | Refined Estimation MDs (Planned) | Time Spent MDs (Consumed) | Burn %`.
- `project_key` must come from local project context config, not hardcoded in code or docs.
