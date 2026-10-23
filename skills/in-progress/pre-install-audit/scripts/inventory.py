#!/usr/bin/env python3
"""List files in a clone. Read-only.

Does not follow symlinks. Does not execute files. Skips the .git directory.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import run_log


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def classify(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if path.is_symlink():
        return f"symlink\t{relative}\t{os.readlink(path)}"
    if not path.is_file():
        return f"other\t{relative}"
    try:
        lines, binary, size = scan_file(path)
    except OSError as exc:
        return f"unreadable\t{relative}\t{exc.__class__.__name__}"
    if binary:
        return f"binary\t{relative}\t{size}"
    return f"file\t{relative}\t{lines}"


def scan_file(path: Path) -> tuple[int, bool, int]:
    lines = 0
    size = 0
    last = b""
    with path.open("rb") as handle:
        head = handle.read(8192)
        size = len(head)
        if b"\0" in head:
            return 0, True, size + _drain(handle)
        lines += head.count(b"\n")
        last = head[-1:] if head else b""
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            lines += chunk.count(b"\n")
            last = chunk[-1:]
    if size and last != b"\n":
        lines += 1
    return lines, False, size


def _drain(handle) -> int:
    extra = 0
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            return extra
        extra += len(chunk)


def inventory(root: Path) -> list[str]:
    rows: list[str] = []
    for dirpath, dirnames, filenames in os_walk_nofollow(root):
        current = Path(dirpath)
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        for name in sorted(dirnames):
            path = current / name
            if path.is_symlink():
                rows.append(classify(root, path))
        for name in sorted(filenames):
            path = current / name
            if not inside(root, current):
                continue
            rows.append(classify(root, path))
    return rows


def os_walk_nofollow(root: Path):
    return os.walk(root, followlinks=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List files in a clone without following symlinks.")
    parser.add_argument("--root", required=True, help="Clone directory to list.")
    parser.add_argument("--run-log", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root)
    log_path = Path(args.run_log)
    if not root.is_dir():
        print("refusing: root is not a directory", file=sys.stderr)
        return 1
    error = run_log.validate_log_path(log_path, root)
    if error:
        print(error, file=sys.stderr)
        return 1
    for row in inventory(root):
        print(row)
    logged = run_log.append_event(log_path, f"python3 scripts/inventory.py --root {root}", [], root)
    if logged:
        print(logged, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
