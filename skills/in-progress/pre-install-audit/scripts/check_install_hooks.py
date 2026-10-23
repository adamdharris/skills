#!/usr/bin/env python3
"""Read-only check for install hooks. Prints file:line hits and changes nothing."""

from __future__ import annotations

import sys

import scanlib


def main(argv: list[str] | None = None) -> int:
    return scanlib.execute("check_install_hooks.py", scanlib.install_hook_hits, argv)


if __name__ == "__main__":
    sys.exit(main())
