# Control: read-only boundary

This file is a control, not an audit item.

The depth-1 retrieval is the only retrieval of the audited code. After `scripts/clone_once.py` returns, the working copy is for reading. Every command is a line in the append-only run log, including the host it contacted, or `-` when it contacted none.

## Allowed commands against the clone

- `python3 scripts/check_install_hooks.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_network.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_processes.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_outside_writes.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_agent_instructions.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_binaries.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_private_data.py --root <clone> --run-log <run-log>`
- `python3 scripts/check_tool_size.py --root <clone> --run-log <run-log>`
- `python3 scripts/inventory.py --root <clone> --run-log <run-log>`
- `python3 scripts/show_lines.py --root <clone> --run-log <run-log> --path <relative-path>`
- `git -C <clone> rev-parse HEAD`
- `git -C <clone> status --porcelain`
- `git -C <clone> branch -a`
- `git -C <clone> tag`

Log a git command with `scripts/run_log.py` before you run it. `git branch` and `git tag` read what the clone already has. They are not a fetch.

## Mark each line

- The run log shows one depth-1 retrieval and no later clone, fetch, or pull.
- The command log shows no package manager, build, test runner, or installer aimed at the clone.
- The command log shows no execution of a file from the clone, including shell scripts and native binaries.
- Submodules were not fetched and were not updated.
- No commit was created in the clone, and nothing was pushed.

Done when each line is met. A line that fails breaks a hard rule in `verdict-rules.md`. Running or fetching the audited project makes the verdict REJECT.
