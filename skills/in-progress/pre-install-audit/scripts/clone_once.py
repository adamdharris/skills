#!/usr/bin/env python3
"""Clone a remote git repository once and print the pinned commit.

Reads the remote once. Does not install, build, or run the cloned project.
Does not fetch again after that clone. A second run with --reuse only
checks out a commit the existing clone already has.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import run_log

REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,200}$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["GIT_NO_LAZY_FETCH"] = "1"
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def containing_repo(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def refuse_destination(dest: Path) -> str | None:
    script_repo = containing_repo(Path(__file__).resolve())
    if script_repo is not None:
        try:
            dest.resolve().relative_to(script_repo.resolve())
        except ValueError:
            return None
        return f"refusing to clone into {dest}: that path is inside {script_repo}"
    return None


def validate_url(url: str) -> str | None:
    if any(char in url for char in "\r\n\t "):
        return "refusing URL: it contains whitespace or a control character"
    if "@" in url and not (url.startswith("git@") or url.startswith("ssh://git@")):
        return "refusing URL: embedded credentials are not accepted"
    if url.startswith("https://"):
        return _validate_https(url)
    if url.startswith("ssh://git@"):
        return _validate_ssh(url)
    if url.startswith("git@") and ":" in url[4:]:
        return _validate_scp(url)
    return "refusing URL: use https://, git@host:path, or ssh://git@host/path"


def _host_ok(host: str) -> str | None:
    if not host or "[" in host or "]" in host:
        return "refusing URL: host is missing or unsupported"
    hostname = host
    if host.count(":") == 1:
        hostname, _, port = host.rpartition(":")
        if not port.isdigit() or not hostname:
            return "refusing URL: bad port"
    elif ":" in host:
        return "refusing URL: host is unsupported"
    if hostname.lower() in LOCAL_HOSTS:
        return "refusing URL: local hosts are out of scope"
    return None


def _validate_https(url: str) -> str | None:
    rest = url[len("https://") :]
    if not rest or "?" in rest or "#" in rest or "@" in rest:
        return "refusing URL: query, fragment, or userinfo is not accepted"
    host, sep, path = rest.partition("/")
    if not sep or not path.strip("/"):
        return "refusing URL: path is missing"
    return _host_ok(host)


def _validate_ssh(url: str) -> str | None:
    rest = url[len("ssh://git@") :]
    if "?" in rest or "#" in rest:
        return "refusing URL: query or fragment is not accepted"
    host, sep, path = rest.partition("/")
    if not sep or not path.strip("/"):
        return "refusing URL: path is missing"
    return _host_ok(host)


def _validate_scp(url: str) -> str | None:
    host, sep, path = url[len("git@") :].partition(":")
    if not sep or not path or path.startswith("/"):
        return "refusing URL: expected git@host:path"
    if "?" in path or "#" in path:
        return "refusing URL: query or fragment is not accepted"
    return _host_ok(host)


def validate_ref(ref: str) -> str | None:
    if not REF_RE.fullmatch(ref) or ".." in ref or ref.endswith("/") or ref.endswith(".lock"):
        return "refusing ref: use a branch, tag, or commit without '..'"
    return None


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=git_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def resolve_commit(dest: Path, ref: str | None) -> tuple[str | None, str | None]:
    spec = "HEAD" if ref is None else f"{ref}^{{commit}}"
    result = run_git(
        ["git", "-C", str(dest), "rev-parse", "--verify", "--end-of-options", spec]
    )
    if result.returncode != 0:
        return None, result.stderr.strip() or result.stdout.strip()
    sha = result.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        return None, "rev-parse did not return a full commit SHA"
    return sha, None


def checkout(dest: Path, sha: str) -> subprocess.CompletedProcess[str]:
    return run_git(
        [
            "git",
            "-C",
            str(dest),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "filter.lfs.required=false",
            "-c",
            "filter.lfs.smudge=",
            "-c",
            "filter.lfs.process=",
            "checkout",
            "--detach",
            "--no-progress",
            sha,
        ]
    )


def local_names(dest: Path) -> str:
    branches = run_git(["git", "-C", str(dest), "branch", "-a", "--format=%(refname:short)"])
    tags = run_git(["git", "-C", str(dest), "tag", "--list"])
    lines = ["refs already in this clone (no fetch was attempted):"]
    if branches.stdout.strip():
        lines.append(branches.stdout.strip())
    if tags.stdout.strip():
        lines.append(tags.stdout.strip())
    if len(lines) == 1:
        lines.append("(none)")
    return "\n".join(lines)


def is_full_sha(ref: str | None) -> bool:
    return bool(ref and SHA_RE.fullmatch(ref))


def host_of(url: str) -> str:
    if url.startswith("https://") or url.startswith("ssh://"):
        rest = url.split("://", 1)[1]
        rest = rest.split("@")[-1]
        return rest.split("/")[0].split(":")[0]
    if url.startswith("git@"):
        return url.split("@", 1)[1].split(":", 1)[0]
    return ""


def clone_argv(url: str, dest: Path, ref: str | None) -> list[str]:
    command = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "protocol.file.allow=never",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--no-recurse-submodules",
        "--config",
        "core.hooksPath=/dev/null",
    ]
    if ref:
        command.extend(["--branch", ref])
    command.extend(["--", url, str(dest)])
    return command


def fetch_argv(dest: Path, sha: str) -> list[str]:
    return [
        "git",
        "-C",
        str(dest),
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "protocol.file.allow=never",
        "fetch",
        "--depth",
        "1",
        "--no-tags",
        "--recurse-submodules=no",
        "origin",
        sha,
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clone a remote repository once and print its commit SHA.")
    parser.add_argument("--url", help="Remote git URL. Required unless --reuse is set.")
    parser.add_argument("--dest", required=True, help="New directory for the clone, outside this skills repository.")
    parser.add_argument("--ref", help="Branch, tag, or full commit SHA to pin at depth 1.")
    parser.add_argument("--run-log", required=True, help="Append-only log. Must sit outside the clone and this repository.")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Do not clone. Check out a commit that dest already contains.",
    )
    args = parser.parse_args(argv)

    if args.ref:
        ref_error = validate_ref(args.ref)
        if ref_error:
            print(ref_error, file=sys.stderr)
            return 1

    dest = Path(args.dest)
    log_path = Path(args.run_log)
    blocked = refuse_destination(dest)
    if blocked:
        print(blocked, file=sys.stderr)
        return 1
    log_error = run_log.validate_log_path(log_path, dest)
    if log_error:
        print(log_error, file=sys.stderr)
        return 1

    if args.reuse:
        if not (dest / ".git").is_dir():
            print("refusing --reuse: dest is not a git clone", file=sys.stderr)
            return 1
        code = _pin(dest, args.ref)
        names = ["--reuse", "--dest", "--run-log"]
        if args.ref:
            names.append("--ref")
        _record(log_path, names, [], code, dest)
        return code

    if not args.url:
        print("refusing: --url is required when --reuse is not set", file=sys.stderr)
        return 1
    url_error = validate_url(args.url)
    if url_error:
        print(url_error, file=sys.stderr)
        return 1
    if dest.exists():
        print("refusing: dest already exists, so this would not be one fresh clone", file=sys.stderr)
        return 1

    host = host_of(args.url)
    created = False
    try:
        if is_full_sha(args.ref):
            code = _clone_sha(args.url, dest, args.ref or "")
        else:
            code = _clone_branch(args.url, dest, args.ref)
        created = dest.exists()
        if code != 0 and created:
            shutil.rmtree(dest, ignore_errors=True)
        names = ["--url", "--dest", "--run-log"]
        if args.ref:
            names.append("--ref")
        _record(log_path, names, [host], code, None)
        return code
    except OSError as exc:
        print(f"clone failed: {exc.__class__.__name__}", file=sys.stderr)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        _record(log_path, ["--url", "--dest", "--run-log"], [host], 3, None)
        return 3


def _record(log_path: Path, arg_names: list[str], hosts: list[str], exit_code: int, deny_root: Path | None) -> None:
    error = run_log.append_event(log_path, "clone_once.py", arg_names, hosts, exit_code, deny_root)
    if error:
        print(error, file=sys.stderr)


def _clone_branch(url: str, dest: Path, ref: str | None) -> int:
    cloned = run_git(clone_argv(url, dest, ref))
    if cloned.returncode != 0:
        sys.stderr.write(cloned.stderr)
        return 3
    return _pin(dest, None)


def _clone_sha(url: str, dest: Path, sha: str) -> int:
    init = run_git(["git", "-c", "core.hooksPath=/dev/null", "init", "--quiet", str(dest)])
    if init.returncode != 0:
        sys.stderr.write(init.stderr)
        return 3
    configured = run_git(["git", "-C", str(dest), "config", "core.hooksPath", "/dev/null"])
    if configured.returncode != 0:
        sys.stderr.write(configured.stderr)
        return 3
    remote = run_git(["git", "-C", str(dest), "remote", "add", "origin", url])
    if remote.returncode != 0:
        sys.stderr.write(remote.stderr)
        return 3
    fetched = run_git(fetch_argv(dest, sha))
    if fetched.returncode != 0:
        sys.stderr.write(fetched.stderr)
        return 3
    return _pin(dest, "FETCH_HEAD")


def _pin(dest: Path, ref: str | None) -> int:
    sha, err = resolve_commit(dest, ref)
    if sha is None:
        print("the ref is not in this clone; not fetching again", file=sys.stderr)
        if err:
            print(err, file=sys.stderr)
        print(local_names(dest), file=sys.stderr)
        return 2
    checked = checkout(dest, sha)
    if checked.returncode != 0:
        sys.stderr.write(checked.stderr)
        return 3
    confirmed, confirm_err = resolve_commit(dest, None)
    if confirmed != sha:
        print(confirm_err or "checkout did not leave HEAD on the pinned SHA", file=sys.stderr)
        return 3
    shallow = run_git(["git", "-C", str(dest), "rev-parse", "--is-shallow-repository"])
    if shallow.stdout.strip() != "true":
        print("warning: the retrieval asked for depth 1 and the result is not shallow", file=sys.stderr)
    print(f"sha={sha}")
    print(f"path={dest.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
