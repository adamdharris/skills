# Audit item: install scripts, postinstall hooks, optional dependencies

Fill report section 2 from `scripts/check_install_hooks.py`.

Mark the item done when every hit is a row that says what the script or dependency does, quoted from its file:line, or the section says there were no hits.

An install script that is read and explained can pass the verdict rule. An install script you did not read fails that rule. Do not run the script.
