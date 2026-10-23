#!/usr/bin/env python3
"""Append one line to the audit run log.

The log is append-only. A line holds the script name, fixed argument names,
hosts, and exit code. It does not hold a free-text command or argument values.
This script never truncates the log, never follows a symlink, and never prints
or writes SOCKET_API_TOKEN.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

SCRIPT_NAMES = {
    "clone_once.py",
    "inventory.py",
    "show_lines.py",
    "socket_supply_chain.py",
    "check_install_hooks.py",
    "check_network.py",
    "check_processes.py",
    "check_outside_writes.py",
    "check_agent_instructions.py",
    "check_binaries.py",
    "check_private_data.py",
    "check_tool_size.py",
    "git",
}
ARG_RE = re.compile(r"^--?[A-Za-z][A-Za-z0-9-]*$")
GIT_WORDS = {"rev-parse", "status", "branch", "tag"}


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


def _fixed_name(value: str, secret: str) -> str | None:
    cleaned = scrub(value.strip(), secret)
    if cleaned in GIT_WORDS or ARG_RE.fullmatch(cleaned):
        return cleaned
    return None


def append_event(
    log_path: Path,
    script: str,
    arg_names: list[str],
    hosts: list[str],
    exit_code: int,
    deny_root: Path | None = None,
) -> str | None:
    error = validate_log_path(log_path, deny_root)
    if error:
        return error
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code < 0 or exit_code > 255:
        return "refusing run log: exit code must be an integer from 0 to 255"
    secret = os.environ.get("SOCKET_API_TOKEN", "")
    script_name = scrub(script.strip(), secret)
    if script_name not in SCRIPT_NAMES:
        return "refusing run log: script name is not a fixed name"
    safe_args: list[str] = []
    for name in arg_names:
        fixed = _fixed_name(name, secret)
        if fixed is None:
            return "refusing run log: argument must be a fixed name"
        safe_args.append(fixed)
    safe_hosts: list[str] = []
    for host in hosts:
        cleaned = scrub(host.strip(), secret)
        if cleaned and all(char.isalnum() or char in ".-" for char in cleaned):
            safe_hosts.append(cleaned)
    host_field = ",".join(safe_hosts) if safe_hosts else "-"
    arg_field = ",".join(safe_args) if safe_args else "-"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp}\tscript={script_name}\targs={arg_field}\thosts={host_field}\texit={exit_code}\n"
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
    parser = argparse.ArgumentParser(description="Append one script record to the run log.")
    parser.add_argument("--log", required=True)
    parser.add_argument("--script", required=True, help="Fixed script name, such as git or clone_once.py.")
    parser.add_argument("--arg", action="append", default=[], help="Fixed argument name. Repeatable. Not a value.")
    parser.add_argument("--host", action="append", default=[])
    parser.add_argument("--exit", required=True, type=int, help="Exit code of the recorded script.")
    parser.add_argument("--deny-root", help="Clone directory. The log must sit outside it.")
    args = parser.parse_args(argv)
    deny = Path(args.deny_root) if args.deny_root else None
    error = append_event(Path(args.log), args.script, args.arg, args.host, args.exit, deny)
    if error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
