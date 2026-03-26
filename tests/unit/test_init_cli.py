from __future__ import annotations

import stat
from pathlib import Path

import pytest

from ws_ctx_engine import init_cli


def test_init_cli_main_sets_executable_and_runs_script(monkeypatch) -> None:
    fake_file = "/repo/src/ws_ctx_engine/init_cli.py"
    expected_script = str(Path(fake_file).parent / "scripts" / "init.sh")

    monkeypatch.setattr(init_cli.os.path, "abspath", lambda _: fake_file)
    monkeypatch.setattr(init_cli.os.path, "dirname", lambda p: str(Path(p).parent))

    chmod_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(init_cli.os, "stat", lambda _: type("_S", (), {"st_mode": 0o640})())
    monkeypatch.setattr(init_cli.os, "chmod", lambda path, mode: chmod_calls.append((path, mode)))
    monkeypatch.setattr(init_cli.os, "getcwd", lambda: "/repo")

    monkeypatch.setattr(init_cli.sys, "argv", ["wsctx-init", "--yes"])

    captured_run: dict[str, object] = {}

    class _RunResult:
        returncode = 0

    def _fake_run(cmd, cwd):
        captured_run["cmd"] = cmd
        captured_run["cwd"] = cwd
        return _RunResult()

    monkeypatch.setattr(init_cli.subprocess, "run", _fake_run)

    with pytest.raises(SystemExit) as exc:
        init_cli.main()

    assert exc.value.code == 0
    assert captured_run == {"cmd": ["bash", expected_script, "--yes"], "cwd": "/repo"}
    assert chmod_calls
    chmod_path, chmod_mode = chmod_calls[0]
    assert chmod_path == expected_script
    assert chmod_mode & stat.S_IEXEC
    assert chmod_mode & stat.S_IXGRP
    assert chmod_mode & stat.S_IXOTH


def test_init_cli_main_exits_with_subprocess_return_code(monkeypatch) -> None:
    monkeypatch.setattr(
        init_cli.os.path, "abspath", lambda _: "/repo/src/ws_ctx_engine/init_cli.py"
    )
    monkeypatch.setattr(init_cli.os.path, "dirname", lambda _: "/repo/src/ws_ctx_engine")
    monkeypatch.setattr(init_cli.os, "stat", lambda _: type("_S", (), {"st_mode": 0o755})())
    monkeypatch.setattr(init_cli.os, "chmod", lambda *_: None)
    monkeypatch.setattr(init_cli.os, "getcwd", lambda: "/repo")
    monkeypatch.setattr(init_cli.sys, "argv", ["wsctx-init"])

    class _RunResult:
        returncode = 17

    monkeypatch.setattr(init_cli.subprocess, "run", lambda *_, **__: _RunResult())

    with pytest.raises(SystemExit) as exc:
        init_cli.main()

    assert exc.value.code == 17
