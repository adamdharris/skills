"""The Socket script must log a request it already sent.

send_once is replaced in-process. No request leaves the test.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import socket_supply_chain  # noqa: E402


def skills_repo() -> Path:
    start = Path(socket_supply_chain.__file__).resolve()
    for parent in start.parents:
        if (parent / ".git").exists():
            return parent
    raise AssertionError("skills repository was not found")


class SocketRunLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.log = self.root / "run.log"
        self.log.write_text("", encoding="utf-8")
        self.calls: list[str] = []

        def fake_send(url: str, token: str, payload: bytes) -> tuple[int, str, bool]:
            self.calls.append(url)
            return 200, '{"ok":true}\n', False

        self.fake_send = fake_send

    def _run(self, output: Path) -> int:
        argv = [
            "--ecosystem",
            "npm",
            "--name",
            "example-pkg",
            "--output",
            str(output),
            "--run-log",
            str(self.log),
            "--execute",
            "--outside-sandbox",
        ]
        with (
            patch.object(socket_supply_chain, "send_once", self.fake_send),
            patch.dict(os.environ, {"SOCKET_API_TOKEN": "fixture-token"}),
            redirect_stderr(StringIO()),
        ):
            return socket_supply_chain.main(argv)

    def test_api_success_outside_the_repository_is_logged(self) -> None:
        output = self.root / "result.json"
        code = self._run(output)
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, ["https://api.socket.dev/v0/purl?alerts=true"])
        self.assertIn("script=socket_supply_chain.py", text)
        self.assertIn("hosts=api.socket.dev", text)
        self.assertIn("exit=0", text)
        self.assertNotIn("fixture-token", text)
        self.assertNotIn("fixture-token", output.read_text(encoding="utf-8"))

    def test_api_success_is_logged_when_output_is_inside_the_skills_repository(self) -> None:
        output = skills_repo() / "socket-result.json"
        self.addCleanup(output.unlink, missing_ok=True)
        self.assertFalse(output.exists())
        code = self._run(output)
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.calls[0].startswith("https://api.socket.dev/"))
        self.assertIn("script=socket_supply_chain.py", text)
        self.assertIn("hosts=api.socket.dev", text)
        self.assertIn("exit=1", text)
        self.assertNotIn("fixture-token", text)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
