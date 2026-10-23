#!/usr/bin/env python3
"""Read-only check for secrets in skill files. Prints a masked file:line preview and changes nothing."""

from __future__ import annotations

import sys

import scanlib


def main(argv: list[str] | None = None) -> int:
    return scanlib.execute("check_private_data.py", scanlib.private_data_hits, argv)


if __name__ == "__main__":
    sys.exit(main())
