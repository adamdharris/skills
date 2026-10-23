# Audit item: network calls and hosts

Fill report section 1 from `scripts/check_network.py`. Patterns are in `references/risk-patterns.md`.

Mark the item done when each hit is a row, or the section says there were no hits.

- Host or URL is the host the script printed, or the URL if you quote it with `show_lines.py`.
- Purpose is one of: telemetry, update check, download, API, or unknown.
- Opt-out is the switch the file documents, or "none found" with the file:line you searched.
- Evidence is `path:line`.

Do not open the host. The check script does not fetch.
