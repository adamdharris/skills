#!/usr/bin/env python3
"""Read-only check for packed binaries. Prints file:line hits and changes nothing."""

from __future__ import annotations

import sys

import scanlib


def main(argv: list[str] | None = None) -> int:
    return scanlib.execute("check_binaries.py", scanlib.binary_hits, argv)


if __name__ == "__main__":
    sys.exit(main())
