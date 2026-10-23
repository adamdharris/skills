# Audit item: child processes, run, attach or inject

Fill report section 3 from `scripts/check_processes.py`.

Mark the item done when each hit names the capability and the trigger on that line, or the section says there were no hits.

Capability is the matched word (`subprocess`, `frida`, a debugger port, and the other patterns in `references/risk-patterns.md`). Trigger is what the same file says causes it, cited at file:line. Do not run the process.
