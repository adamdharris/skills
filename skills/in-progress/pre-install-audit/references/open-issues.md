# Audit item: open issues and PRs with risk words

Fill report section 8. Search words: malware, fake, clone, token, injection, security.

The check scripts do not fetch issues or pull requests. When the operator pastes matching issues or pull requests from the git host, record the title, state, a one-line summary, and the link, and append that host to the run log with `scripts/run_log.py`. When none were supplied, write a single row whose summary is "not run".

Mark the item done when the table is filled that way. A "not run" row does not by itself choose REJECT.
