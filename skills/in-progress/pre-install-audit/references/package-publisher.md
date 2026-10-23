# Audit item: package and publisher match

Fill report section 9.

- Read the package name, the exact version, and the repository field from the manifest with `scripts/show_lines.py`. Cite those lines.
- Publisher match uses the manifest author or publisher field and the supply-chain result. Cite both.
- Lookalike repos or packages are recorded only from evidence already in the clone or in the supply-chain result. Do not run a registry search from a check script.

Mark the item done when the three rows are yes or no with evidence. An unexplained publisher mismatch is REJECT. A mismatch you can explain fails the match rule and blocks ADOPT, and the verdict is PIN AND HARDEN unless a REJECT rule also applies.
