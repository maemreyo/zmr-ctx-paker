from __future__ import annotations

from pathlib import Path


class WorkspacePathGuard:
    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def resolve_relative(self, requested_path: str) -> Path:
        candidate = Path(requested_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.workspace_root / candidate).resolve()

        if not self._is_within_workspace(resolved):
            raise PermissionError("ACCESS_DENIED: Path resolves outside workspace boundary.")

        return resolved

    def to_relative_posix(self, absolute_path: Path) -> str:
        return absolute_path.resolve().relative_to(self.workspace_root).as_posix()

    def _is_within_workspace(self, path: Path) -> bool:
        try:
            path.relative_to(self.workspace_root)
            return True
        except ValueError:
            return False
