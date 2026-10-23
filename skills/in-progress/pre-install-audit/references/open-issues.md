# Audit item: open issues and PRs with risk words

Fill report section 8. Search words: malware, fake, clone, token, injection, security.

The check scripts do not fetch issues or pull requests. When the operator pastes matching issues or pull requests from the git host, record the title, state, a one-line summary, and the link in the report. Append only the host to the run log: `scripts/run_log.py --log "<run-log>" --script git --host "<host>" --exit <code>`. Do not put the pasted title, summary, or link in the run log. When none were supplied, write a single row whose summary is "not run".

Mark the item done when the table is filled that way. A "not run" row does not by itself choose REJECT.
