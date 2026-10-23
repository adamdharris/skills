# Changelog

## Unreleased

- Scaffold for public skills: a marketplace catalog with no plugin entries, an empty promoted bucket, policy docs, and one issue template.
- In-progress skill `pre-install-audit`: a read-only audit of a third-party repository that ends in one report with a verdict and file and line evidence. The skill is not in the catalog.
- The same skill now audits the nine report sections, runs eight read-only checks, and uses the verdicts ADOPT, PIN AND HARDEN, and REJECT. Retrieval is depth 1. WebFetch is removed while the skill is active. Commands and hosts go to an append-only run log.
