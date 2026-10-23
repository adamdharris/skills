# Audit item: files written outside its own folder

Fill report section 4 from `scripts/check_outside_writes.py`.

Mark the item done when each hit has the path, when it is written, and whether it is agent config, a skill, a hook, or memory.

A write to an agent config, skill, hook, or memory path fails the verdict rule unless the report quotes an opt-in at file:line. Do not write those paths yourself.
