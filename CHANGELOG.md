# Changelog

## Unreleased

- The scaffold adds a marketplace catalog with no plugin entries. The promoted bucket is empty. The scaffold adds policy files and one issue template.
- The in-progress skill `pre-install-audit` does a read-only audit of a third-party repository. The audit makes one report. The report has a verdict and file and line evidence. The marketplace catalog does not list this skill.
- The skill now audits the nine report sections. The skill runs eight read-only checks. The verdicts are ADOPT, PIN AND HARDEN, and REJECT. Retrieval uses depth 1. The skill removes WebFetch while the skill is active. The run log records the script name, argument names, hosts, and exit code.
