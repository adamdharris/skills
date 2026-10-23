#!/usr/bin/env python3
"""Read-only size check. The token count is an estimate. Changes nothing."""

from __future__ import annotations

import sys

import scanlib


def main(argv: list[str] | None = None) -> int:
    return scanlib.execute("check_tool_size.py", scanlib.tool_size_hits, argv)


if __name__ == "__main__":
    sys.exit(main())
