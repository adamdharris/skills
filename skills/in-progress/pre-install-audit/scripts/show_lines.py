#!/usr/bin/env python3
"""Print numbered lines from one file inside a root. Read-only.

Refuses to follow a symlink that leaves the root. Does not execute the file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import run_log

MAX_LINE = 500


def resolve_inside(root: Path, relative: str) -> Path | str:
    if relative.startswith("/") or relative.startswith("\\") or "\\" in relative:
        return "refusing path: use a relative path inside the root"
    parts = Path(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return "refusing path: '..' and absolute paths are not accepted"
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            target = current.resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                return "refusing path: symlink leaves the root"
    resolved = current.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return "refusing path: resolved path leaves the root"
    return current


def format_line(relative: str, number: int, text: str) -> str:
    body = text.replace("\t", " ")
    if len(body) > MAX_LINE:
        body = body[:MAX_LINE] + " [truncated]"
    return f"{relative}:{number}: {body}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print path:line quotes from one file.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--run-log", required=True)
    parser.add_argument("--path", required=True, help="Path relative to root.")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0, help="Last line to print. 0 means through the end.")
    args = parser.parse_args(argv)
    if args.start < 1 or args.end < 0:
        print("refusing: line numbers start at 1", file=sys.stderr)
        return 1

    root = Path(args.root)
    log_path = Path(args.run_log)
    if not root.is_dir():
        print("refusing: root is not a directory", file=sys.stderr)
        return 1
    error = run_log.validate_log_path(log_path, root)
    if error:
        print(error, file=sys.stderr)
        return 1

    def finish(code: int) -> int:
        logged = run_log.append_event(
            log_path,
            f"python3 scripts/show_lines.py --root {root} --path {args.path}",
            [],
            root,
        )
        if logged:
            print(logged, file=sys.stderr)
            return 1
        return code

    located = resolve_inside(root, args.path)
    if isinstance(located, str):
        print(located, file=sys.stderr)
        return finish(1)
    if not located.is_file():
        print("refusing: path is not a file", file=sys.stderr)
        return finish(1)
    if located.stat().st_size > 1_000_000:
        print("refusing: file is larger than 1000000 bytes", file=sys.stderr)
        return finish(2)

    blob = located.read_bytes()
    if b"\0" in blob[:8192]:
        print("refusing: file looks binary, so there are no text lines to quote", file=sys.stderr)
        return finish(2)

    relative = Path(args.path).as_posix()
    text = blob.decode("utf-8", errors="replace").splitlines()
    end = args.end if args.end else len(text)
    printed = 0
    for number, line in enumerate(text, start=1):
        if number < args.start or number > end:
            continue
        print(format_line(relative, number, line))
        printed += 1
    if printed == 0:
        print("no lines in the requested range", file=sys.stderr)
        return finish(2)
    return finish(0)


if __name__ == "__main__":
    sys.exit(main())
