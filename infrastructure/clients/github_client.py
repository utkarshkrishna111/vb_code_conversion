"""
GitHub MCP Client

Typed async wrapper around the vb2py-github MCP server.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from infrastructure.clients.base_client import BaseMCPClient

_SERVER = str(Path(__file__).parent.parent / "servers" / "github_server.py")


class GitHubClient(BaseMCPClient):
    server_script = _SERVER

    def __init__(self) -> None:
        super().__init__()

    async def create_pr(
        self,
        module_name: str,
        python_file_path: Path,
        python_code: str,
        test_results_summary: str,
    ) -> Optional[str]:
        raw = await self._call(
            "create_pr",
            module_name=module_name,
            python_file_path=str(python_file_path),
            python_code=python_code,
            test_results_summary=test_results_summary,
        )
        return json.loads(raw).get("url")
