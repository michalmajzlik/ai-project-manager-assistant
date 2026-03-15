# Outputs

## Structure
- `reports/daily` - generated daily project reports and live daily Jira snapshots
- `reports/weekly` - generated weekly management reports and live weekly Jira snapshots
- `meetings` - meeting-specific outputs grouped by source
- `examples` - sample report templates and example outputs
- `tests` - temporary or validation outputs used during pipeline testing

## Naming
- keep generated reports in their type folder
- use date in filename when the output is time-bound
- keep one-off validation artifacts in `tests` instead of the root
