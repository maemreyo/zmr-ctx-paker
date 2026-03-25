from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from context_packer.mcp.security.path_guard import WorkspacePathGuard
from context_packer.mcp.security.rade_delimiter import RADESession


def test_workspace_path_guard_to_relative_posix_and_inside_absolute() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "src" / "app.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")

        guard = WorkspacePathGuard(str(root))
        resolved = guard.resolve_relative(str(target))
        relative = guard.to_relative_posix(resolved)

    assert relative == "src/app.py"


def test_workspace_path_guard_to_relative_posix_raises_outside_workspace() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as outside:
        guard = WorkspacePathGuard(workspace)
        outside_path = Path(outside) / "outside.py"
        outside_path.write_text("x = 1\n", encoding="utf-8")

        with pytest.raises(ValueError):
            guard.to_relative_posix(outside_path)


def test_rade_session_markers_and_wrap_shape() -> None:
    session = RADESession(session_token="deadbeefdeadbeef")
    start, end = session.markers_for("src/auth.py")
    wrapped = session.wrap("src/auth.py", "print('ok')")

    assert start == "CTX_deadbeefdeadbeef:content_start:src/auth.py"
    assert end == "CTX_deadbeefdeadbeef:content_end"
    assert wrapped["content_start_marker"] == start
    assert wrapped["content_end_marker"] == end
    assert wrapped["content"].startswith(start)
    assert wrapped["content"].endswith(end)
