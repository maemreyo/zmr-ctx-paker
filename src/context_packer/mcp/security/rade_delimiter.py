from __future__ import annotations

import secrets


class RADESession:
    def __init__(self, session_token: str | None = None) -> None:
        self._session_token = session_token or secrets.token_hex(8)

    def markers_for(self, path: str) -> tuple[str, str]:
        start_marker = f"CTX_{self._session_token}:content_start:{path}"
        end_marker = f"CTX_{self._session_token}:content_end"
        return start_marker, end_marker

    def wrap(self, path: str, content: str) -> dict[str, str]:
        start_marker, end_marker = self.markers_for(path)
        wrapped = f"{start_marker}\n{content}\n{end_marker}"
        return {
            "content_start_marker": start_marker,
            "content": wrapped,
            "content_end_marker": end_marker,
        }
