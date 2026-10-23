#!/usr/bin/env python3
"""Shared read-only scanners for the pre-install audit checks.

Imports nothing that installs, builds, runs, or fetches. Prints are the
caller's job. Patterns match references/risk-patterns.md.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

import run_log

TEXT_LIMIT = 1_000_000
SKIP_DIRS = {".git"}
PACKED_EXTENSIONS = {".exe", ".dll", ".so", ".dylib", ".bin", ".node", ".wasm", ".jar"}
INSTALL_KEYS = ("preinstall", "install", "postinstall", "prepare")

URL_RE = re.compile(r"https?://([^/\s'\"<>]+)", re.IGNORECASE)
NET_WORD_RE = re.compile(
    r"\b(fetch|axios|requests|urllib|curl|wget|telemetry|update-check|update_check|updateCheck|http)\b",
    re.IGNORECASE,
)
PROCESS_RE = re.compile(
    r"child_process|\bspawn\b|\bexec(?:Sync|File)?\b|subprocess|os\.system|\bfrida\b|\bptrace\b|"
    r"debugger attach|Debugger\.attach|remote-debugging-port|DevTools|:(?:9222|9229)\b",
    re.IGNORECASE,
)
OUTSIDE_RE = re.compile(
    r"~/\.claude|(?:/|\\)\.claude\b|~/\.cursor|(?:/|\\)\.cursor\b|~/\.codex|(?:/|\\)\.codex\b|"
    r"\.mcp\.json|settings\.json|CLAUDE\.md|AGENTS\.md|"
    r"(?:/|\\)hooks(?=/|\\|\b)|(?:(?<=[\s'\"`])|^)hooks/|"
    r"(?:/|\\)skills(?=/|\\|\b)|(?:(?<=[\s'\"`])|^)skills/|"
    r"(?:/|\\)memory(?=/|\\|\b)|(?:(?<=[\s'\"`])|^)memory/"
)
AGENT_RE = re.compile(
    r"@latest|npx\s+-y|npx\s+--yes|no approval|without asking|bypassPermissions|--dangerously-skip-permissions"
)
PEM_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
PREFIX_RE = re.compile(
    r"\b(?:ghp_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|sk-[A-Za-z0-9]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|"
    r"AKIA[0-9A-Z]{8,}|glpat-[A-Za-z0-9_\-]{8,})"
)
ASSIGN_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*[\"']?([^\s\"']{8,})"
)
HOME_RE = re.compile(r"(?:~?/home/[A-Za-z0-9._-]+|~?/Users/[A-Za-z0-9._-]+|~/?\.ssh)\b")
PLACEHOLDER_RE = re.compile(r"(?i)^(your|example|changeme|placeholder|todo|xxx+|redacted|none|null|<.*>)$")
SCRIPT_KEY_RE = re.compile(r'"(preinstall|install|postinstall|prepare)"\s*:')
OPTIONAL_KEY_RE = re.compile(r'"optionalDependencies"\s*:')


def preview(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value)
    if len(cleaned) >= 4:
        return cleaned[:4]
    if len(cleaned) >= 2:
        return cleaned[:2]
    return cleaned


def _walk_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        dirnames[:] = sorted(
            name for name in dirnames if name not in SKIP_DIRS and not (current / name).is_symlink()
        )
        for name in sorted(filenames):
            path = current / name
            if path.is_symlink():
                continue
            yield path


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_text(path: Path) -> str | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > TEXT_LIMIT:
        return None
    try:
        blob = path.read_bytes()
    except OSError:
        return None
    if b"\0" in blob[:8192]:
        return None
    return blob.decode("utf-8", errors="replace")


def _lines(path: Path) -> list[str] | None:
    text = _read_text(path)
    if text is None:
        return None
    return text.splitlines()


def install_hook_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        name = path.name
        lines = _lines(path)
        if lines is None:
            continue
        rel = _relative(root, path)
        if name == "package.json":
            hits.extend(_package_json_hooks(rel, lines))
        elif name == "setup.py":
            for number, line in enumerate(lines, start=1):
                if "cmdclass" in line or "ext_modules" in line:
                    hits.append(f"{rel}:{number}: setup hook")
        elif name == "pyproject.toml":
            for number, line in enumerate(lines, start=1):
                if "build-backend" in line or "cmdclass" in line or "hook" in line.lower():
                    hits.append(f"{rel}:{number}: pyproject hook")
    return hits


def _package_json_hooks(rel: str, lines: list[str]) -> list[str]:
    hits: list[str] = []
    in_optional = False
    depth = 0
    for number, line in enumerate(lines, start=1):
        for match in SCRIPT_KEY_RE.finditer(line):
            hits.append(f"{rel}:{number}: {match.group(1)}")
        cursor = 0
        if not in_optional:
            key = OPTIONAL_KEY_RE.search(line)
            if not key:
                continue
            hits.append(f"{rel}:{number}: optionalDependencies")
            in_optional = True
            depth = 0
            cursor = key.end()
        fragment = line[cursor:]
        index = 0
        while index < len(fragment):
            char = fragment[index]
            if char == "{":
                depth += 1
                index += 1
                continue
            if char == "}":
                depth -= 1
                index += 1
                if depth <= 0:
                    in_optional = False
                    break
                continue
            if char == '"':
                end = fragment.find('"', index + 1)
                if end < 0:
                    break
                token = fragment[index + 1 : end]
                rest = fragment[end + 1 :].lstrip()
                if depth == 1 and rest.startswith(":") and token != "optionalDependencies":
                    hits.append(f"{rel}:{number}: optionalDependency {token}")
                index = end + 1
                continue
            index += 1
    return hits


def network_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        lines = _lines(path)
        if lines is None:
            continue
        rel = _relative(root, path)
        for number, line in enumerate(lines, start=1):
            hosts = []
            for host in URL_RE.findall(line):
                hostname = host.split("@")[-1].split(":")[0]
                if hostname and hostname not in hosts:
                    hosts.append(hostname)
            for host in hosts:
                hits.append(f"{rel}:{number}: host={host}")
            remainder = URL_RE.sub(" ", line)
            seen: set[str] = set()
            for word in NET_WORD_RE.findall(remainder):
                key = word.lower()
                if key in seen:
                    continue
                seen.add(key)
                hits.append(f"{rel}:{number}: {word}")
    return hits


def process_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        lines = _lines(path)
        if lines is None:
            continue
        rel = _relative(root, path)
        for number, line in enumerate(lines, start=1):
            seen: set[str] = set()
            for found in PROCESS_RE.finditer(line):
                text = found.group(0)
                if text in seen:
                    continue
                seen.add(text)
                hits.append(f"{rel}:{number}: {text}")
    return hits


def outside_write_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        lines = _lines(path)
        if lines is None:
            continue
        rel = _relative(root, path)
        for number, line in enumerate(lines, start=1):
            seen: set[str] = set()
            for found in OUTSIDE_RE.finditer(line):
                text = found.group(0).strip()
                if text in seen:
                    continue
                seen.add(text)
                hits.append(f"{rel}:{number}: {text}")
    return hits


def _is_skill_file(path: Path) -> bool:
    return path.name == "SKILL.md" or path.name.lower() == "skill.md"


def agent_instruction_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        lines = _lines(path)
        if lines is None:
            continue
        rel = _relative(root, path)
        skill = _is_skill_file(path)
        for number, line in enumerate(lines, start=1):
            seen: set[str] = set()
            for found in AGENT_RE.finditer(line):
                text = found.group(0)
                if text in seen:
                    continue
                seen.add(text)
                hits.append(f"{rel}:{number}: {text}")
            if skill and "allowed-tools" in line:
                hits.append(f"{rel}:{number}: allowed-tools")
    return hits


def _magic_kind(path: Path) -> str | None:
    try:
        blob = path.read_bytes()[:4]
    except OSError:
        return None
    if blob.startswith(b"MZ"):
        return "magic mz"
    if blob.startswith(b"\x7fELF"):
        return "magic elf"
    if blob.startswith(b"\xfe\xed\xfa") or blob.startswith(b"\xcf\xfa\xed\xfe") or blob.startswith(b"\xca\xfe\xba\xbe"):
        return "magic macho"
    return None


def binary_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        rel = _relative(root, path)
        suffix = path.suffix.lower()
        if suffix in PACKED_EXTENSIONS:
            hits.append(f"{rel}:1: extension {suffix}")
            continue
        kind = _magic_kind(path)
        if kind:
            hits.append(f"{rel}:1: {kind}")
    return hits


def _skill_instruction(path: Path) -> bool:
    if _is_skill_file(path):
        return True
    return "references" in path.parts


def private_data_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in _walk_files(root):
        if not _skill_instruction(path):
            continue
        lines = _lines(path)
        if lines is None:
            continue
        rel = _relative(root, path)
        for number, line in enumerate(lines, start=1):
            secret = _secret_preview(line)
            if secret:
                hits.append(f"{rel}:{number}: secret preview={secret}")
    return hits


def _secret_preview(line: str) -> str | None:
    if PEM_RE.search(line):
        return preview("----")
    prefixed = PREFIX_RE.search(line)
    if prefixed:
        return preview(prefixed.group(0))
    assigned = ASSIGN_RE.search(line)
    if assigned and not PLACEHOLDER_RE.match(assigned.group(1)):
        return preview(assigned.group(1))
    home = HOME_RE.search(line)
    if home:
        return preview(home.group(0))
    return None


def _description_chars(path: Path) -> int:
    lines = _lines(path)
    if lines is None:
        return 0
    total = 0
    if _is_skill_file(path):
        in_front = False
        for line in lines:
            if line.strip() == "---":
                if not in_front:
                    in_front = True
                    continue
                break
            if in_front and line.startswith("description:"):
                total += len(line.split(":", 1)[1].strip())
    if path.suffix == ".json":
        try:
            data = json.loads("\n".join(lines))
        except json.JSONDecodeError:
            data = None
        tools = data.get("tools") if isinstance(data, dict) else None
        if isinstance(tools, list):
            for item in tools:
                if isinstance(item, dict) and isinstance(item.get("description"), str):
                    total += len(item["description"])
    return total


def _tool_names(path: Path) -> list[str]:
    if path.suffix != ".json":
        return []
    lines = _lines(path)
    if lines is None:
        return []
    try:
        data = json.loads("\n".join(lines))
    except json.JSONDecodeError:
        return []
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, list):
        return []
    names = []
    for item in tools:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return names


def tool_size_hits(root: Path) -> list[str]:
    skills: list[str] = []
    tool_files: list[str] = []
    tool_names: list[tuple[str, str]] = []
    desc_chars = 0
    for path in _walk_files(root):
        rel = _relative(root, path)
        desc_chars += _description_chars(path)
        if _is_skill_file(path):
            skills.append(rel)
        if "tools" in path.parts and path.suffix.lower() in {".py", ".js", ".ts", ".mjs", ".sh", ".md", ".json"}:
            tool_files.append(rel)
        for name in _tool_names(path):
            tool_names.append((rel, name))
    tool_count = len(tool_files) + len(tool_names)
    tokens = math.ceil(desc_chars / 4) if desc_chars else 0
    lazy = "yes" if len(skills) + len(tool_files) > 1 else "no"
    lines = [
        f"tools: {tool_count}",
        f"skills: {len(skills)}",
        f"estimated_tokens: {tokens}",
        "method: characters/4",
        f"lazy_load_possible: {lazy}",
    ]
    for rel in skills:
        lines.append(f"{rel}:1: skill")
    for rel in tool_files:
        lines.append(f"{rel}:1: tool file")
    for rel, name in tool_names:
        lines.append(f"{rel}:1: tool {name}")
    return lines


CHECKS = {
    "check_install_hooks.py": install_hook_hits,
    "check_network.py": network_hits,
    "check_processes.py": process_hits,
    "check_outside_writes.py": outside_write_hits,
    "check_agent_instructions.py": agent_instruction_hits,
    "check_binaries.py": binary_hits,
    "check_private_data.py": private_data_hits,
    "check_tool_size.py": tool_size_hits,
}


def execute(script_name: str, scanner, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only file:line check. Changes nothing.")
    parser.add_argument("--root", required=True)
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
    hits = scanner(root)
    for line in hits:
        print(line)
    logged = run_log.append_event(
        log_path,
        f"python3 scripts/{script_name} --root {root} --run-log {log_path}",
        [],
        root,
    )
    if logged:
        print(logged, file=sys.stderr)
        return 1
    return 0
