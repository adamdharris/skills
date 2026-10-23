# Checklist: read-only boundary

The clone is the only retrieval of the audited code. After `scripts/clone_once.py` returns, the working copy is for reading.

## Allowed commands against the clone

- `python3 scripts/inventory.py --root <clone>`
- `python3 scripts/show_lines.py --root <clone> --path <relative-path>`
- `git -C <clone> rev-parse HEAD`
- `git -C <clone> status --porcelain`
- `git -C <clone> branch -a`
- `git -C <clone> tag`

`git branch` and `git tag` here read what the clone already has. They are not a fetch.

## Mark each line

- The command log shows one `clone_once.py` invocation and no second clone, fetch, or pull.
- The command log shows no package manager, build, test runner, or installer aimed at the clone.
- The command log shows no execution of a file from the clone, including shell scripts and native binaries.
- Submodules were not fetched and were not updated.
- No commit was created in the clone, and nothing was pushed.

Done when each line is met. A line that fails breaks a hard rule in `verdict-rules.md`, and the verdict is fail.
