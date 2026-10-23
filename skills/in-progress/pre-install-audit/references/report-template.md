# Report template

Copy this skeleton into a new file outside this skills repository and outside the clone. Fill the blanks. Leave the headings and the table columns as they are.

# Pre-install audit: <tool-name>

| Field | Value |
|---|---|
| Repo URL | <https://github.com/org/repo> |
| Commit SHA (full) | <40-character SHA> |
| Package and version | <npm or PyPI name>@<exact version>, or "none" |
| Publisher | <registry publisher> |
| Audit date (AEST) | <YYYY-MM-DD HH:MM> |
| Auditor skill version | pre-install-audit skill v<x.y>, run by <person> |
| Sandbox | <Vercel Sandbox (region) or local Docker fallback>; network after clone: <off or allow list> |
| Socket result | <green / amber / red / not run>, link: <url> |
| Verdict | <ADOPT / PIN AND HARDEN / REJECT> |

## Summary

Three lines or fewer: what it is, the main risk, and the verdict.

## 1. Network calls and hosts

| Host or URL | Purpose (telemetry, update check, download, API) | Opt-out | Evidence file:line |
|---|---|---|---|
| | | | |

## 2. Install scripts, postinstall hooks, optional dependencies

| Script or dependency | What it does | Evidence file:line |
|---|---|---|
| | | |

## 3. Child processes, run, attach or inject

| Capability | Trigger | Evidence file:line |
|---|---|---|
| | | |

## 4. Files written outside its own folder

| Path | When | Agent config, skill, hook or memory? | Evidence file:line |
|---|---|---|---|
| | | | |

## 5. What its skill and instruction files tell the agent to do

| Instruction (quoted, short) | Risk (for example @latest, no approval needed) | Evidence file:line |
|---|---|---|
| | | |

## 6. Tool count and token cost

Tools: <n>. Skills: <n>. Estimated tokens for descriptions: <n> (estimate, method: <method>).

Lazy-load possible: <yes or no>.

## 7. Overlap with what is installed

| Installed item | Overlap | Keep, replace or skip |
|---|---|---|
| | | |

## 8. Open issues and PRs with risk words

Search words: malware, fake, clone, token, injection, security.

| Issue or PR | State | Summary | Link |
|---|---|---|---|
| | | | |

## 9. Package and publisher match

| Check | Result | Evidence |
|---|---|---|
| Registry repo field matches this repo | <yes or no> | <link> |
| Publisher matches repo owner | <yes or no> | <link> |
| Lookalike repos or packages seen | <yes or no> | <links> |

## Risk table

| # | Risk | Severity (high, medium, low) | Evidence file:line | Mitigation |
|---|---|---|---|---|
| | | | | |

## Verdict rule check

| Rule | Result |
|---|---|
| Socket result is green | <pass or fail> |
| No bypassPermissions or --dangerously-skip-permissions | <pass or fail> |
| No @latest or unpinned fetch in instructions | <pass or fail> |
| No install scripts, or each one is read and explained | <pass or fail> |
| No writes to agent configs without an opt-in | <pass or fail> |
| Package and publisher match the repo | <pass or fail> |
| Every risk has a checked file:line | <pass or fail> |

## Verdict: <ADOPT / PIN AND HARDEN / REJECT>

Reasons: <one line for each reason, with the risk number>.

## Pin and harden instructions

Exact pin: <package>@<x.y.z> or git <SHA>. Turn off auto-update: <how>.

Scope: <project scope, not user scope>. Settings to add: <deny rules, env opt-outs>.

Back up configs before install, and check the diff after: <paths>.

## Evidence check

Each file:line above was opened again by the verify pass: <yes, n of n>.

Secrets seen: masked as file:line plus a 2 to 4 character preview, never the value.
