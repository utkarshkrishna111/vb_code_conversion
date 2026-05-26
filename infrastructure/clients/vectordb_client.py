"""
VectorDB MCP Client

Typed async wrapper around the vb2py-vectordb MCP server.
"""
from __future__ import annotations

import json
from pathlib import Path

from infrastructure.clients.base_client import BaseMCPClient

_SERVER = str(Path(__file__).parent.parent / "servers" / "vectordb_server.py")


class VectorDBClient(BaseMCPClient):
    server_script = _SERVER

    def __init__(self, use_memory: bool = False) -> None:
        super().__init__("--memory") if use_memory else super().__init__()

    async def store_pattern(
        self, java_snippet: str, python_snippet: str, description: str
    ) -> None:
        await self._call(
            "store_pattern",
            java_snippet=java_snippet,
            python_snippet=python_snippet,
            description=description,
        )

    async def search_patterns(self, java_snippet: str, top_k: int = 3) -> list[dict]:
        raw = await self._call("search_patterns", java_snippet=java_snippet, top_k=top_k)
        return json.loads(raw)
