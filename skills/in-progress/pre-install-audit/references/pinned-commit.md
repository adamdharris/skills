# Checklist: pinned commit

The audit names one full commit. A branch or tag is resolved during the one clone, and the report then uses the SHA.

Mark each line met or failed.

- The report records the repository URL that was cloned.
- The report records the ref the user passed, or records that no ref was passed.
- `scripts/clone_once.py` printed `sha=` as 40 hexadecimal digits.
- `git -C <clone> rev-parse HEAD` prints that same SHA.
- Later notes in the report name that SHA. They do not switch back to a branch name.

Done when those lines are met and the SHA in the report header is the SHA from the clone. If the ref was not in the clone, the item is failed, the verdict is inconclusive until a SHA is pinned, and you do not fetch again.
