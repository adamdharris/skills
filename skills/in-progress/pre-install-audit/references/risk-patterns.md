# Risk patterns

The read-only checks search for these patterns and print file:line hits. They do not install, build, run, or fetch. A hit is a lead for the report. The line decides whether it is a real risk.

## Install hooks

`scripts/check_install_hooks.py`

- In `package.json`: the script names `preinstall`, `install`, `postinstall`, and `prepare`, and the object `optionalDependencies` with each dependency name under it.
- In `setup.py`: `cmdclass` and `ext_modules`.
- In `pyproject.toml`: `build-backend`, `cmdclass`, and a line that contains `hook`.

## Network

`scripts/check_network.py`

- An `http://` or `https://` URL. The hit prints the host, not the rest of the URL.
- The words `fetch`, `axios`, `requests`, `urllib`, `curl`, `wget`, `telemetry`, `update-check`, `update_check`, `updateCheck`, and `http` as its own word.

## Processes and injection

`scripts/check_processes.py`

- `child_process`, `spawn`, `exec`, `execSync`, `execFile`, `subprocess`, `os.system`.
- `frida`, `ptrace`, `debugger attach`, `Debugger.attach`.
- `remote-debugging-port`, `DevTools`, and the port markers `:9222` and `:9229`.

## Writes outside the folder

`scripts/check_outside_writes.py`

- `~/.claude`, `~/.cursor`, `~/.codex`, and the same directories written as `/.claude`, `/.cursor`, and `/.codex`.
- `.mcp.json`, `settings.json`, `CLAUDE.md`, `AGENTS.md`.
- Path segments `hooks`, `skills`, and `memory` when a slash or backslash marks them as a path.

## Agent instructions

`scripts/check_agent_instructions.py`

- `@latest`
- `npx -y` and `npx --yes`
- `no approval`
- `without asking`
- `bypassPermissions`
- `--dangerously-skip-permissions`
- `allowed-tools` when the file is `SKILL.md`

## Binaries

`scripts/check_binaries.py`

- Extensions `.exe`, `.dll`, `.so`, `.dylib`, `.bin`, `.node`, `.wasm`, `.jar`.
- File magic for MZ, ELF, and Mach-O. The hit names the kind. It does not print bytes.

## Private data in skill files

`scripts/check_private_data.py` reads `SKILL.md` and files under `references/` only.

- A PEM private-key header.
- Token prefixes `ghp_`, `github_pat_`, `sk-`, `xox`, `AKIA`, `glpat-`.
- An assignment of `api_key`, `api-key`, `secret`, `token`, `password`, or `passwd` whose value is not a placeholder (`your`, `example`, `changeme`, `placeholder`, `todo`, `xxx`, `redacted`, `none`, `null`).
- A path under `/home/`, `/Users/`, or `.ssh`.

The printed hit is `secret preview=` plus 2 to 4 characters. The value is not printed.

## Tool and skill size

`scripts/check_tool_size.py`

- A skill is one `SKILL.md`.
- A tool is a file under a `tools/` directory (`.py`, `.js`, `.ts`, `.mjs`, `.sh`, `.md`, `.json`) or a named entry in a JSON `tools` array.
- Estimated tokens are the description characters divided by 4, rounded up. The method label is `characters/4`. Descriptions are the `description` field in `SKILL.md` frontmatter and the `description` strings on JSON tools. The number is an estimate.
- `lazy_load_possible` is `yes` when the skill count plus the tool-file count is greater than 1, and `no` otherwise. That is a heuristic for the report, not a measurement.
