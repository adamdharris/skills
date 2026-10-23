#!/usr/bin/env python3
"""Append one line to the audit run log.

The log is append-only. This script never truncates it, never follows a
symlink, and never prints or writes SOCKET_API_TOKEN.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


def containing_repo(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def scrub(text: str, secret: str) -> str:
    if not text or not secret:
        return text
    redacted = text.replace(secret, "[redacted]")
    encoded = quote(secret, safe="")
    if encoded and encoded != secret:
        redacted = redacted.replace(encoded, "[redacted]")
    return redacted


def _inside(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def validate_log_path(log_path: Path, deny_root: Path | None = None) -> str | None:
    if log_path.is_symlink():
        return "refusing run log: path is a symlink"
    repo = containing_repo(Path(__file__).resolve())
    if repo is not None and _inside(repo, log_path):
        return "refusing run log: path is inside the skills repository"
    if deny_root is not None and _inside(deny_root, log_path):
        return "refusing run log: path is inside the clone"
    parent = log_path.parent
    if not parent.is_dir():
        return "refusing run log: parent directory does not exist"
    if parent.is_symlink():
        return "refusing run log: parent directory is a symlink"
    return None


def append_event(log_path: Path, command: str, hosts: list[str], deny_root: Path | None = None) -> str | None:
    error = validate_log_path(log_path, deny_root)
    if error:
        return error
    secret = os.environ.get("SOCKET_API_TOKEN", "")
    safe_command = scrub(command.replace("\n", " ").replace("\r", " "), secret)[:500]
    safe_hosts: list[str] = []
    for host in hosts:
        cleaned = scrub(host.strip(), secret)
        if cleaned and all(char.isalnum() or char in ".-" for char in cleaned):
            safe_hosts.append(cleaned)
    host_field = ",".join(safe_hosts) if safe_hosts else "-"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp}\tcommand={safe_command}\thosts={host_field}\n"
    if secret and secret in line:
        line = scrub(line, secret)
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(log_path, flags, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append one command to the run log.")
    parser.add_argument("--log", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--host", action="append", default=[])
    parser.add_argument("--deny-root", help="Clone directory. The log must sit outside it.")
    args = parser.parse_args(argv)
    deny = Path(args.deny_root) if args.deny_root else None
    error = append_event(Path(args.log), args.command, args.host, deny)
    if error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
