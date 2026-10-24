"""Regression tests for pinning a non-default branch and for a failed pin.

The script refuses file:// URLs. These tests allow the file transport only in
this process so git can read a local bare repository. The assertions are the
SHA the command prints and whether a later clone is rejected.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import clone_once  # noqa: E402


def run(args: list[str]) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout


def make_two_branch_remote(root: Path) -> tuple[str, str, str]:
    bare = root / "src.git"
    work = root / "work"
    run(["git", "init", "-b", "main", "--bare", str(bare)])
    run(["git", "init", "-b", "main", str(work)])
    run(["git", "-C", str(work), "config", "user.email", "dev@example.com"])
    run(["git", "-C", str(work), "config", "user.name", "Dev"])
    run(["git", "-C", str(work), "config", "commit.gpgsign", "false"])
    (work / "README").write_text("main line\n", encoding="utf-8")
    run(["git", "-C", str(work), "add", "README"])
    run(["git", "-C", str(work), "commit", "-q", "-m", "main"])
    run(["git", "-C", str(work), "checkout", "-q", "-b", "feature"])
    (work / "README").write_text("feature line\n", encoding="utf-8")
    run(["git", "-C", str(work), "add", "README"])
    run(["git", "-C", str(work), "commit", "-q", "-m", "feature"])
    run(["git", "-C", str(work), "push", "-q", str(bare), "main", "feature"])
    main_sha = run(["git", "-C", str(work), "rev-parse", "main"]).strip()
    feature_sha = run(["git", "-C", str(work), "rev-parse", "feature"]).strip()
    return f"file://{bare}", main_sha, feature_sha


def invoke(argv: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = clone_once.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


@contextmanager
def local_fixture_clone():
    original_argv = clone_once.clone_argv
    original_validate = clone_once.validate_url

    def argv(url: str, dest: Path, ref: str | None) -> list[str]:
        command = original_argv(url, dest, ref)
        cleaned: list[str] = []
        index = 0
        while index < len(command):
            blocked = (
                command[index] == "-c"
                and index + 1 < len(command)
                and command[index + 1] == "protocol.file.allow=never"
            )
            if blocked:
                index += 2
                continue
            cleaned.append(command[index])
            index += 1
        return cleaned

    clone_once.clone_argv = argv
    clone_once.validate_url = lambda url: None
    try:
        yield
    finally:
        clone_once.clone_argv = original_argv
        clone_once.validate_url = original_validate


class CloneOncePinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.url, self.main_sha, self.feature_sha = make_two_branch_remote(self.root)
        self.dest = self.root / "clone"
        self.log = self.root / "run-log" / "audit.log"
        self.log.parent.mkdir()
        self.log.write_text("", encoding="utf-8")

    def test_non_default_branch_pins_that_commit(self) -> None:
        with local_fixture_clone():
            code, stdout, stderr = invoke(
                ["--url", self.url, "--dest", str(self.dest), "--ref", "feature", "--run-log", str(self.log)]
            )
        self.assertEqual(code, 0, stderr)
        self.assertIn(f"sha={self.feature_sha}", stdout)
        self.assertNotIn(self.main_sha, stdout)
        head = run(["git", "-C", str(self.dest), "rev-parse", "HEAD"]).strip()
        self.assertEqual(head, self.feature_sha)

    def test_reuse_resolves_a_short_branch_name(self) -> None:
        with local_fixture_clone():
            first, _stdout, first_err = invoke(
                ["--url", self.url, "--dest", str(self.dest), "--ref", "feature", "--run-log", str(self.log)]
            )
            self.assertEqual(first, 0, first_err)
            code, stdout, stderr = invoke(
                ["--reuse", "--dest", str(self.dest), "--ref", "feature", "--run-log", str(self.log)]
            )
        self.assertEqual(code, 0, stderr)
        self.assertIn(f"sha={self.feature_sha}", stdout)
        self.assertNotIn(self.main_sha, stdout)

    def test_failed_pin_lets_the_documented_clone_run_again(self) -> None:
        real_pin = clone_once._pin
        failed = {"once": False}

        def fail_once(dest: Path, ref: str | None) -> int:
            if not failed["once"]:
                failed["once"] = True
                return 2
            return real_pin(dest, ref)

        with local_fixture_clone():
            clone_once._pin = fail_once
            try:
                code, stdout, stderr = invoke(
                    ["--url", self.url, "--dest", str(self.dest), "--ref", "feature", "--run-log", str(self.log)]
                )
                self.assertEqual(code, 2, stderr)
                self.assertFalse(self.dest.exists(), stderr)
                self.assertNotIn("sha=", stdout)
                code, stdout, stderr = invoke(
                    ["--url", self.url, "--dest", str(self.dest), "--ref", "feature", "--run-log", str(self.log)]
                )
            finally:
                clone_once._pin = real_pin
        self.assertEqual(code, 0, stderr)
        self.assertNotIn("dest already exists", stderr)
        self.assertIn(f"sha={self.feature_sha}", stdout)


if __name__ == "__main__":
    unittest.main()
