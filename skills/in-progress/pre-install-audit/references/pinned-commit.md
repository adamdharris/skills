# Control: pinned commit

This file is a control, not an audit item.

The audit names one full commit. The retrieval is depth 1. A branch or tag is `git clone --depth 1`. A full SHA is one `git fetch --depth 1` of that commit. The report then uses the SHA.

Mark each line met or failed.

- The report records the repository URL that was cloned.
- The report records the ref the user passed, or records that no ref was passed.
- `scripts/clone_once.py` used `--depth 1` and printed `sha=` as 40 hexadecimal digits.
- `git -C <clone> rev-parse HEAD` prints that same SHA.
- Later notes in the report name that SHA. They do not switch back to a branch name.

Done when those lines are met and the Commit SHA header is the SHA from the clone. If the ref was not in that depth-1 retrieval, stop. Do not fetch again. The verdict cannot be ADOPT until a SHA is pinned.
